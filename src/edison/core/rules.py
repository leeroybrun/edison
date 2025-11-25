"""
Edison Rules Engine and Rules Composition.

This module contains two related systems:

1. RulesRegistry / compose_rules:
   - Load rule metadata from YAML registries (core + packs)
   - Resolve guideline anchors (<!-- ANCHOR: name --> ... <!-- END ANCHOR: name -->)
   - Apply include resolution via the composition engine
   - Produce a composed, machine-readable rules view for CLIs and tooling

2. RulesEngine:
   - Enforce per-project rules at task state transitions based on project config overlays
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import fnmatch
import subprocess
import yaml

from .composition import resolve_includes, ComposeError
from .evidence import EvidenceManager
from .paths import EdisonPathError, PathResolver
from .paths.project import get_project_config_dir
from .paths.management import get_management_paths
from edison.core.utils.subprocess import run_with_timeout


class AnchorNotFoundError(KeyError):
    """Raised when a referenced guideline anchor cannot be found."""

    pass


class RulesCompositionError(RuntimeError):
    """Raised when rule registry loading or composition fails."""

    pass


class RulesRegistry:
    """
    Load and compose rules from core + pack YAML registries.

    Registry locations (relative to project root):
      - Core: .edison/core/rules/registry.yml
      - Packs: .edison/packs/<pack>/rules/registry.yml

    This class is read-only; it does not mutate project state.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        try:
            self.project_root = project_root or PathResolver.resolve_project_root()
        except (EdisonPathError, ValueError) as exc:  # pragma: no cover - defensive
            raise RulesCompositionError(str(exc)) from exc

        self.core_registry_path = (
            self.project_root / ".edison" / "core" / "rules" / "registry.yml"
        )
        self.packs_root = self.project_root / ".edison" / "packs"
        self.project_config_dir = get_project_config_dir(self.project_root)

    # ------------------------------------------------------------------
    # Registry loading
    # ------------------------------------------------------------------
    @staticmethod
    def _load_yaml(path: Path, *, required: bool) -> Dict[str, Any]:
        if not path.exists():
            if required:
                raise RulesCompositionError(f"Rules registry not found at {path}")
            return {"version": None, "rules": []}

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: expected mapping at top level"
            )

        rules = data.get("rules") or []
        if not isinstance(rules, list):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: 'rules' must be a list"
            )
        data["rules"] = rules
        return data

    def load_core_registry(self) -> Dict[str, Any]:
        """Load core rules registry from .edison/core/rules/registry.yml."""
        return self._load_yaml(self.core_registry_path, required=True)

    def load_pack_registry(self, pack_name: str) -> Dict[str, Any]:
        """Load pack-specific rules registry if it exists; otherwise empty."""
        path = self.packs_root / pack_name / "rules" / "registry.yml"
        return self._load_yaml(path, required=False)

    # ------------------------------------------------------------------
    # Anchor resolution
    # ------------------------------------------------------------------
    @staticmethod
    def extract_anchor_content(source_file: Path, anchor: str) -> str:
        """
        Extract content between ANCHOR markers in a guideline file.

        Supports both explicit END markers and implicit termination at the next
        ANCHOR marker (or EOF when no END marker is present).
        """
        if not source_file.exists():
            raise FileNotFoundError(f"Guideline file not found: {source_file}")

        lines = source_file.read_text(encoding="utf-8").splitlines()
        start_idx: Optional[int] = None
        end_idx: Optional[int] = None

        start_marker = f"<!-- ANCHOR: {anchor} -->"
        end_marker = f"<!-- END ANCHOR: {anchor} -->"
        # Any ANCHOR start (used to detect implicit end)
        anchor_start_re = re.compile(r"<!--\s*ANCHOR:\s*.+?-->")

        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i + 1  # content begins after the marker
                break

        if start_idx is None:
            raise AnchorNotFoundError(f"Anchor '{anchor}' not found in {source_file}")

        for j in range(start_idx, len(lines)):
            line = lines[j]
            if end_marker in line:
                end_idx = j
                break
            if anchor_start_re.search(line):
                end_idx = j
                break

        if end_idx is None:
            end_idx = len(lines)

        body_lines = lines[start_idx:end_idx]
        body = "\n".join(body_lines).rstrip()
        if body:
            body += "\n"
        return body

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------
    def _resolve_source(self, rule: Dict[str, Any]) -> Tuple[Optional[Path], Optional[str]]:
        """Resolve source file path and optional anchor for a rule."""
        source = rule.get("source") or {}
        file_ref = str(source.get("file") or rule.get("sourcePath") or "").strip()
        anchor = source.get("anchor")

        if not file_ref:
            return None, None

        # Legacy form: "path#anchor" embedded in sourcePath
        file_part, sep, frag = file_ref.partition("#")
        if sep and frag and not anchor:
            anchor = frag
        else:
            file_part = file_ref

        # Resolve file path: absolute-from-root when starting with .edison/project-config-dir/ or /
        project_dir_prefix = f"{self.project_config_dir.name}/"
        if file_part.startswith(project_dir_prefix):
            source_path = (self.project_config_dir / file_part[len(project_dir_prefix):]).resolve()
        elif file_part.startswith((".edison/", "/")):
            source_path = (self.project_root / file_part.lstrip("/")).resolve()
        else:
            # Treat as relative to core directory (e.g., "guidelines/VALIDATION.md")
            source_path = (self.project_root / ".edison" / "core" / file_part).resolve()

        return source_path, str(anchor) if anchor else None

    def _compose_rule_body(
        self,
        rule: Dict[str, Any],
        origin: str,
        *,
        deps: Optional[Set[Path]] = None,
    ) -> Tuple[str, List[Path]]:
        """
        Build composed body text for a single rule.

        Composition semantics:
          - If source.file (+ optional anchor) is present, extract anchor content
            or entire file, then resolve {{include:...}} patterns via the
            prompt composition engine.
          - Append inline ``guidance`` text after resolved anchor content.
        """
        if deps is None:
            deps = set()

        source_file, anchor = self._resolve_source(rule)

        body_parts: List[str] = []

        if source_file is not None:
            if anchor:
                anchor_text = self.extract_anchor_content(source_file, anchor)
            else:
                anchor_text = source_file.read_text(encoding="utf-8")

            body_parts.append(anchor_text)

            # Resolve any include directives within the anchor text.
            try:
                resolved_text, include_deps = resolve_includes(
                    "".join(body_parts),
                    base_file=source_file,
                )
            except ComposeError as exc:
                # Surface a composition-aware error while preserving details
                raise RulesCompositionError(str(exc)) from exc

            deps.update(include_deps)
            body_parts = [resolved_text]

        guidance = rule.get("guidance")
        if guidance:
            guidance_text = str(guidance).rstrip()
            if guidance_text:
                if body_parts and not body_parts[-1].endswith("\n"):
                    body_parts[-1] += "\n"
                body_parts.append(guidance_text + "\n")

        body = "".join(body_parts) if body_parts else ""
        return body, sorted({p.resolve() for p in deps})

    def compose(self, packs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compose rules from core + optional packs into a single structure.

        Returns:
            Dict with keys:
              - version: registry version (string)
              - packs: list of packs used during composition
              - rules: mapping of rule-id -> composed rule payload
        """
        packs = list(packs or [])

        core = self.load_core_registry()
        rules_index: Dict[str, Dict[str, Any]] = {}

        # Core rules first
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue

            body, deps = self._compose_rule_body(raw_rule, origin="core")
            entry: Dict[str, Any] = {
                "id": rid,
                "title": raw_rule.get("title") or rid,
                "category": raw_rule.get("category") or "",
                "blocking": bool(raw_rule.get("blocking", False)),
                "contexts": raw_rule.get("contexts") or [],
                "source": raw_rule.get("source") or {},
                "body": body,
                "origins": ["core"],
                "dependencies": [str(p) for p in deps],
            }
            rules_index[rid] = entry

        # Pack overlays merge by rule id
        for pack_name in packs:
            pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue

                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin=f"pack:{pack_name}",
                )

                if rid not in rules_index:
                    rules_index[rid] = {
                        "id": rid,
                        "title": raw_rule.get("title") or rid,
                        "category": raw_rule.get("category") or "",
                        "blocking": bool(raw_rule.get("blocking", False)),
                        "contexts": raw_rule.get("contexts") or [],
                        "source": raw_rule.get("source") or {},
                        "body": body,
                        "origins": [f"pack:{pack_name}"],
                        "dependencies": [str(p) for p in deps],
                    }
                    continue

                entry = rules_index[rid]
                # Title: allow pack to refine title when provided
                if raw_rule.get("title"):
                    entry["title"] = raw_rule["title"]
                # Category: allow pack to refine category when provided
                if raw_rule.get("category"):
                    entry["category"] = raw_rule["category"]
                # Blocking: once blocking, always blocking
                if raw_rule.get("blocking", False):
                    entry["blocking"] = True
                # Contexts: append pack contexts
                if raw_rule.get("contexts"):
                    entry["contexts"] = (entry.get("contexts") or []) + raw_rule["contexts"]  # type: ignore[index]
                # Body: append pack guidance after core text
                entry["body"] = (entry.get("body") or "") + (body or "")
                # Origins: record pack contribution
                entry.setdefault("origins", []).append(f"pack:{pack_name}")
                # Dependencies: merge without duplicates
                existing = set(entry.get("dependencies") or [])
                for p in deps:
                    existing.add(str(p))
                entry["dependencies"] = sorted(existing)

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }


def compose_rules(packs: Optional[List[str]] = None, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience wrapper for composing rules via RulesRegistry.

    Used by tests and CLI entrypoints.

    Args:
        packs: List of pack names to include (optional)
        project_root: Project root path (optional, defaults to PathResolver.resolve_project_root())
    """
    registry = RulesRegistry(project_root=project_root)
    return registry.compose(packs=packs)


@dataclass
class Rule:
    """A single enforceable rule."""

    id: str
    description: str
    enforced: bool = True
    blocking: bool = False
    reference: Optional[str] = None  # Path to guideline/doc
    # Optional per-rule configuration payload (YAML → dict)
    # Example for validator-approval:
    #   config:
    #     requireReport: true
    #     maxAgeDays: 7
    config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.blocking and not self.enforced:
            raise ValueError(f"Rule {self.id}: blocking rules must be enforced")


@dataclass
class RuleViolation:
    """A rule that was violated."""

    rule: Rule
    task_id: str
    message: str
    severity: str  # 'blocking' or 'warning'


class RulesEngine:
    """
    Enforces per-project rules based on task state and type.

    Rules are defined in project config overlays under the 'rules:' section.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize rules engine from config.

        Args:
            config: Full Edison config (from ConfigManager().load_config())
        """
        self.rules_config = config.get("rules", {}) if isinstance(config, dict) else {}
        self.enforcement_enabled = self.rules_config.get("enforcement", True)

        # Parse rules by category
        self.rules_by_state = self._parse_rules(self.rules_config.get("byState", {}))
        self.rules_by_type = self._parse_rules(self.rules_config.get("byTaskType", {}))
        self.project_rules = self._parse_rule_list(self.rules_config.get("project", []))

        # Lazy cache for context-aware rule lookup
        self._all_rules_cache: Optional[List[Rule]] = None

    def _parse_rules(self, rules_dict: Dict[str, List[Dict]]) -> Dict[str, List[Rule]]:
        """Parse rules dictionary into Rule objects."""
        parsed: Dict[str, List[Rule]] = {}
        for key, rule_list in (rules_dict or {}).items():
            parsed[key] = self._parse_rule_list(rule_list or [])
        return parsed

    def _parse_rule_list(self, rule_list: List[Dict]) -> List[Rule]:
        """Parse list of rule dicts into Rule objects."""
        # Accept unknown keys conservatively by passing through to dataclass; this
        # allows optional fields like `config` to flow in without breaking older
        # rules that may not define them.
        return [Rule(**rule_dict) for rule_dict in (rule_list or [])]

    # ------------------------------------------------------------------
    # Context-aware rule selection (Phase 1B)
    # ------------------------------------------------------------------
    def _iter_all_rules(self) -> List[Rule]:
        """Return all unique rules from state, type, and project scopes."""
        if self._all_rules_cache is not None:
            return self._all_rules_cache

        seen: set[str] = set()
        ordered: List[Rule] = []

        def _add(rule: Rule) -> None:
            if rule.id in seen:
                return
            seen.add(rule.id)
            ordered.append(rule)

        for rules in (self.rules_by_state or {}).values():
            for r in rules or []:
                _add(r)
        for rules in (self.rules_by_type or {}).values():
            for r in rules or []:
                _add(r)
        for r in self.project_rules or []:
            _add(r)

        self._all_rules_cache = ordered
        return ordered

    def _detect_changed_files(self) -> List[Path]:
        """Best-effort detection of changed files via git status.

        This helper is intentionally conservative:
        - Returns an empty list on any error (no git, not a repo, etc.).
        - Considers both staged and unstaged changes, plus untracked files.
        """
        try:
            root = PathResolver.resolve_project_root()
        except EdisonPathError:
            return []

        try:
            result = run_with_timeout(
                ["git", "status", "--porcelain"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            return []

        paths: List[Path] = []
        for line in (result.stdout or "").splitlines():
            if not line.strip():
                continue
            # Format: XY <path>
            if len(line) < 4:
                continue
            path_str = line[3:].strip()
            if not path_str:
                continue
            paths.append((root / path_str).resolve())
        return paths

    def get_rules_for_context(
        self,
        context_type: str,
        task_state: Optional[str] = None,
        changed_files: Optional[List[Path]] = None,
        operation: Optional[str] = None,
    ) -> List[Rule]:
        """
        Return applicable rules for a given runtime context.

        Context metadata is carried in each rule's ``config.contexts`` list,
        where every entry may define:
          - type:        guidance|delegation|validation|transition|...
          - states:      list of task states (e.g. ['todo', 'wip'])
          - operations:  list of operation identifiers (e.g. 'tasks/status')
          - filePatterns:list of glob patterns relative to project root
          - priority:    integer priority (lower values returned first)

        The helper intentionally fails open when no matching rules are
        configured, returning an empty list rather than raising.
        """
        ctx = (context_type or "").strip().lower()
        if not ctx:
            return []

        # Normalise changed_files to repo-relative strings when possible.
        rel_paths: List[str] = []
        files_to_use: List[Path] = list(changed_files or [])
        if not files_to_use:
            files_to_use = self._detect_changed_files()

        if files_to_use:
            try:
                root = PathResolver.resolve_project_root()
            except EdisonPathError:
                root = None
            for p in files_to_use:
                path = Path(p)
                try:
                    if root is not None:
                        rel = path.resolve().relative_to(root)
                        rel_paths.append(str(rel).replace("\\", "/"))
                        continue
                except Exception:
                    pass
                rel_paths.append(str(path).replace("\\", "/"))

        task_state_norm = (task_state or "").strip().lower() or None
        op_norm = (operation or "").strip() or None

        candidates: List[Tuple[int, str, Rule]] = []

        for rule in self._iter_all_rules():
            cfg = rule.config or {}
            ctx_entries = cfg.get("contexts") or []
            if not isinstance(ctx_entries, list):
                continue

            matched = False
            for entry in ctx_entries:
                if not isinstance(entry, dict):
                    continue

                entry_type = str(entry.get("type") or "").strip().lower()
                if entry_type != ctx:
                    continue

                # Optional state filter
                states = entry.get("states")
                if task_state_norm and isinstance(states, list):
                    states_norm = {str(s).strip().lower() for s in states}
                    if task_state_norm not in states_norm:
                        continue

                # Optional operation filter
                ops = entry.get("operations")
                if op_norm and isinstance(ops, list) and ops:
                    ops_norm = {str(o).strip() for o in ops}
                    if op_norm not in ops_norm:
                        continue

                # Optional file pattern filter
                patterns = entry.get("filePatterns") or []
                if patterns:
                    if not rel_paths:
                        # Patterns configured but no changed files provided:
                        # treat as non-match rather than assume global applicability.
                        continue
                    pat_list = [str(pat) for pat in patterns]
                    if not any(
                        fnmatch.fnmatch(path, pat)
                        for path in rel_paths
                        for pat in pat_list
                    ):
                        continue

                priority = int(entry.get("priority") or cfg.get("priority") or 100)
                candidates.append((priority, rule.id, rule))
                matched = True
                break  # One matching context entry is enough

            # No matching context entry → skip; guidance fallback handled below.
            if matched:
                continue

        # Fallback: for guidance contexts with no explicit metadata, surface
        # non-blocking project-wide rules as low-priority hints.
        if not candidates and ctx == "guidance":
            for rule in self.project_rules or []:
                if rule.blocking:
                    continue
                priority = int((rule.config or {}).get("priority", 100))
                candidates.append((priority, rule.id, rule))

        candidates.sort(key=lambda t: (t[0], t[1]))
        return [r for _, _, r in candidates]

    # ------------------------------------------------------------------
    # State machine guard helpers (Phase 1B)
    # ------------------------------------------------------------------
    def check_transition_guards(
        self,
        from_state: str,
        to_state: str,
        task: Dict[str, Any],
        session: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check high-level guard conditions for a task state transition.

        This helper is intentionally lightweight and focuses on core
        invariants that are independent of any particular CLI:

        Guard set (Phase 1B):

        - todo → wip:
            Task must be claimed by the session (`task.session_id == session.id`).
        - wip → done:
            Implementation report JSON must exist in the evidence tree.
        - done → validated:
            All blocking validators in ``validation_results.blocking_validators``
            must have ``passed=True``.
        - done → wip:
            Requires an explicit rollback reason on the task.
        """
        from_norm = str(from_state or "").strip().lower()
        to_norm = str(to_state or "").strip().lower()

        if from_norm == "todo" and to_norm == "wip":
            sid_task = str(task.get("session_id") or task.get("sessionId") or "").strip()
            sid_session = str((session or {}).get("id") or "").strip()
            if not sid_task or not sid_session or sid_task != sid_session:
                return False, "Task not claimed by this session"
            return True, None

        if from_norm == "wip" and to_norm == "done":
            task_id = str(task.get("id") or "").strip()
            if not task_id:
                return False, "Task id is required to verify implementation report"
            try:
                root = PathResolver.resolve_project_root()
            except EdisonPathError:
                return False, "Cannot resolve project root to verify implementation report"
            mgmt_paths = get_management_paths(root)
            ev_root = mgmt_paths.get_qa_root() / "validation-evidence" / task_id
            if not ev_root.exists():
                return False, "Implementation report required before transitioning wip → done (no evidence directory)"
            rounds = sorted([p for p in ev_root.glob("round-*") if p.is_dir()])
            for rd in reversed(rounds):
                if (rd / "implementation-report.json").exists():
                    return True, None
            return False, "Implementation report required before transitioning wip → done"

        if from_norm == "done" and to_norm == "validated":
            vr = validation_results or {}
            blocking = vr.get("blocking_validators") or []
            failed = [v for v in blocking if not v.get("passed")]
            if failed:
                names = [
                    str(v.get("name") or v.get("id") or "") for v in failed if v
                ]
                return False, f"Blocking validators failed: {names}"
            return True, None

        if from_norm == "done" and to_norm == "wip":
            reason = str(
                task.get("rollbackReason")
                or task.get("rollback_reason")
                or ""
            ).strip()
            if not reason:
                return False, "Rollback reason is required when moving task from done → wip"
            return True, None

        # Default: no additional guards defined → allow.
        return True, None

    def check_state_transition(
        self, task: Dict[str, Any], from_state: str, to_state: str
    ) -> List[RuleViolation]:
        """
        Check rules before allowing state transition.

        Args:
            task: Task object with metadata
            from_state: Current task state
            to_state: Target task state

        Returns:
            List of rule violations (blocking violations will prevent transition)

        Raises:
            RuleViolationError: If blocking rule fails
        """
        if not self.enforcement_enabled:
            return []

        violations: List[RuleViolation] = []

        # Get rules for target state + task-type + project-wide (dedup by id)
        state_rules = self.rules_by_state.get(to_state, [])
        extra_rules = self.get_rules_for_task(task)
        seen = {r.id for r in state_rules}
        applicable_rules = [*state_rules, *[r for r in extra_rules if r.id not in seen]]

        for rule in applicable_rules:
            if not rule.enforced:
                continue

            # Check rule (delegate to specific checkers)
            passed = self._check_rule(task, rule)

            if not passed:
                violation = RuleViolation(
                    rule=rule,
                    task_id=task.get("id", "unknown"),
                    message=f"Failed to satisfy rule: {rule.description}",
                    severity="blocking" if rule.blocking else "warning",
                )
                violations.append(violation)

                if rule.blocking:
                    raise RuleViolationError(
                        f"Blocking rule failed for task {task.get('id')} (rule: {rule.id}): {rule.description}",
                        violations=[violation],
                    )

        return violations

    def get_rules_for_task(self, task: Dict[str, Any]) -> List[Rule]:
        """
        Get all applicable rules for a task based on type.

        Args:
            task: Task object

        Returns:
            List of applicable rules
        """
        task_type = task.get("projectTaskType") or task.get("type")

        rules: List[Rule] = []

        # Task-type specific rules
        if task_type and task_type in self.rules_by_type:
            rules.extend(self.rules_by_type[task_type])

        # Project-wide rules
        rules.extend(self.project_rules)

        return rules

    def _check_rule(self, task: Dict[str, Any], rule: Rule) -> bool:
        """
        Check if task satisfies a rule.

        This is a basic implementation. Extend with specific checkers.

        Args:
            task: Task object
            rule: Rule to check

        Returns:
            True if rule is satisfied, False otherwise
        """
        # Basic rule checking logic
        # Can be extended with rule-specific validators

        if rule.id == "task-definition-complete":
            return bool(task.get("acceptanceCriteria"))

        if rule.id == "all-tests-pass":
            # Check test results (would integrate with TDD system)
            test_status = task.get("testStatus", {})
            return bool(test_status.get("allPass", False))

        if rule.id == "coverage-threshold":
            # Check coverage (would integrate with TDD system)
            coverage = task.get("coverage", {})
            return bool(coverage.get("meetsThreshold", False))

        if rule.id == "validator-approval":
            return self._check_validator_approval(task, rule)

        # Default: conservative failure when rule is not explicitly handled.
        # This ensures new rules produce at least a warning until a checker exists.
        return False

    def validate_config(self) -> List[str]:
        """
        Validate rules configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[str] = []

        # Check for duplicate rule IDs across all rule sets
        all_rule_ids: set[str] = set()
        for rules in self.rules_by_state.values():
            for rule in rules:
                if rule.id in all_rule_ids:
                    errors.append(f"Duplicate rule ID: {rule.id}")
                all_rule_ids.add(rule.id)

        for rules in self.rules_by_type.values():
            for rule in rules:
                if rule.id in all_rule_ids:
                    errors.append(f"Duplicate rule ID: {rule.id}")
                all_rule_ids.add(rule.id)

        for rule in self.project_rules:
            if rule.id in all_rule_ids:
                errors.append(f"Duplicate rule ID: {rule.id}")
            all_rule_ids.add(rule.id)

        # Include project-scoped rules in duplicate and invalid checks
        for rules in list(self.rules_by_state.values()) + list(self.rules_by_type.values()) + [self.project_rules]:
            for rule in rules:
                if rule.blocking and not rule.enforced:
                    errors.append(f"Rule {rule.id}: blocking rules must be enforced")

        return errors

    # -------------------------
    # Rule-specific checkers
    # -------------------------

    def _load_json_safe(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _check_validator_approval(self, task: Dict[str, Any], rule: Rule) -> bool:
        """Check if task has a valid, recent validator bundle approval.

        Semantics (fail-closed, EvidenceManager-backed):
          - Locate bundle-approved.json for the latest evidence round:
              <management_dir>/qa/validation-evidence/<task-id>/round-N/bundle-approved.json
            using EvidenceManager (honours AGENTS_PROJECT_ROOT, project_ROOT, etc.).
          - Require the bundle file to exist (requireReport=True) and be fresh
            based on maxAgeDays.
          - Require bundle.approved == True.
          - When approved == False, surface failing/missing validators in the error.

        Config (rule.config):
          - requireReport (bool, default True)
          - maxAgeDays (int, default 7)
        """
        # Normalize config with safe defaults
        cfg = rule.config if isinstance(getattr(rule, "config", None), dict) else {}
        require_report = bool(cfg.get("requireReport", True))
        try:
            max_age_days = int(cfg.get("maxAgeDays", 7))
        except Exception:
            max_age_days = 7

        task_id = str(task.get("id") or task.get("taskId") or "").strip() or "unknown"
        validation = task.get("validation") or {}
        explicit_path = validation.get("reportPath") or validation.get("path")

        def _raise(message: str) -> None:
            violation = RuleViolation(
                rule=rule,
                task_id=str(task_id),
                message=message,
                severity="blocking" if rule.blocking else "warning",
            )
            raise RuleViolationError(message, [violation])

        # ------------------------------------------------------------------
        # Resolve bundle path
        # ------------------------------------------------------------------
        bundle_path: Optional[Path] = None

        if explicit_path:
            # Caller provided an explicit report path on the task.
            p = Path(str(explicit_path))
            if not p.is_absolute():
                try:
                    root = PathResolver.resolve_project_root()
                except EdisonPathError:
                    # Fallback for partially migrated environments
                    root = Path(__file__).resolve().parents[3]
                p = root / p
            bundle_path = p
        else:
            # Derive from evidence rounds when no explicit path is provided.
            if not require_report:
                # Config explicitly allows missing bundle; treat as pass.
                return True
            try:
                latest_round = EvidenceManager.get_latest_round_dir(str(task_id))
            except FileNotFoundError:
                # No evidence directory or no round-* dirs present.
                root = PathResolver.resolve_project_root()
                evidence_dir = get_management_paths(root).get_qa_root() / "validation-evidence" / str(task_id)
                try:
                    rel = evidence_dir.relative_to(root)
                except Exception:
                    rel = evidence_dir
                _raise(
                    f"No evidence rounds found for task {task_id} under {rel}"
                )
            else:
                bundle_path = latest_round / "bundle-approved.json"

        # If we still do not have a path, treat as pass when not required.
        if bundle_path is None:
            return True

        # Sanity check existence
        if not bundle_path.exists():
            if require_report:
                _raise(
                    f"Validation bundle summary missing for task {task_id}: {bundle_path} "
                    "(bundle-approved.json not found)"
                )
            return False

        # Age check (mtime)
        try:
            mtime = datetime.fromtimestamp(bundle_path.stat().st_mtime, tz=timezone.utc)
        except Exception:
            # Preserve previous fail-open semantics on timestamp issues.
            mtime = datetime.now(timezone.utc)
        age_ok = (datetime.now(timezone.utc) - mtime) <= timedelta(days=max_age_days)
        if not age_ok:
            _raise(
                f"Validation bundle summary expired for task {task_id}: {bundle_path} "
                f"(older than {max_age_days} days)"
            )

        # Content check: bundle-approved.json must contain approved: true
        data = self._load_json_safe(bundle_path)
        if not data:
            if require_report:
                _raise(
                    f"Invalid or empty bundle-approved.json for task {task_id}: "
                    f"{bundle_path}"
                )
            return False

        approved = bool(data.get("approved"))
        if not approved:
            # Derive failing/missing validators from bundle payload for diagnostics.
            failing_validators: list[str] = []

            validators = data.get("validators") or []
            if isinstance(validators, list):
                for entry in validators:
                    if not isinstance(entry, dict):
                        continue
                    vid = str(
                        entry.get("validatorId") or entry.get("id") or ""
                    ).strip()
                    v_approved = entry.get("approved")
                    verdict = str(entry.get("verdict") or "").lower()
                    if v_approved is False or verdict in {"reject", "blocked"}:
                        if vid:
                            failing_validators.append(vid)

            missing = data.get("missing") or []
            if isinstance(missing, list):
                for m in missing:
                    if m:
                        failing_validators.append(str(m))

            details = ""
            if failing_validators:
                uniq = sorted({v for v in failing_validators})
                details = f"; failing or missing validators: {', '.join(uniq)}"

            _raise(
                f"Validation bundle not approved for task {task_id}: "
                f"bundle-approved.json approved=false{details}"
            )

        return True


class RuleViolationError(Exception):
    """Raised when a blocking rule is violated."""

    def __init__(self, message: str, violations: List[RuleViolation]):
        super().__init__(message)
        self.violations = violations


__all__ = [
    "AnchorNotFoundError",
    "RulesCompositionError",
    "RulesRegistry",
    "compose_rules",
    "Rule",
    "RuleViolation",
    "RulesEngine",
    "RuleViolationError",
]
