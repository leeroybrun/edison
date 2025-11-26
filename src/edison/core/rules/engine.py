"""
Rules Engine for the Edison Rules system.

This module provides the RulesEngine class for enforcing per-project rules
based on task state and type. Rules are defined in project config overlays.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.paths import get_management_paths
from edison.core.utils.subprocess import run_with_timeout
from edison.data import read_yaml

from .models import Rule, RuleViolation
from .errors import RuleViolationError
from . import checkers


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

    # ------------------------------------------------------------------
    # Role-based rule query API (Phase T-005)
    # ------------------------------------------------------------------
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """
        Load all rules from the bundled registry.

        Returns:
            List of rule dictionaries from the registry
        """
        registry_data = read_yaml("rules", "registry.yml")
        rules = registry_data.get("rules", [])
        return rules if isinstance(rules, list) else []

    @classmethod
    def get_rules_for_role(cls, role: str) -> List[Dict[str, Any]]:
        """
        Extract rules that apply to a specific role.

        Args:
            role: One of 'orchestrator', 'agent', 'validator'

        Returns:
            List of rule dictionaries where applies_to includes the role

        Raises:
            ValueError: If role is not one of the valid options
        """
        if role not in ('orchestrator', 'agent', 'validator'):
            raise ValueError(f"Invalid role: {role}. Must be orchestrator, agent, or validator")

        all_rules = cls.get_all()
        return [
            rule for rule in all_rules
            if role in rule.get('applies_to', [])
        ]

    @classmethod
    def filter_rules(cls, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter rules by context metadata (role, category, etc.).

        This classmethod API provides simplified filtering of rules from the
        bundled registry, complementing the instance method get_rules_for_context
        which works with Rule objects for runtime enforcement.

        Args:
            context: Dictionary with optional keys:
                - role: One of 'orchestrator', 'agent', 'validator'
                - category: Rule category (e.g., 'validation', 'delegation')

        Returns:
            List of rule dictionaries matching the context filters
        """
        rules = cls.get_all()

        # Filter by role if specified
        if 'role' in context:
            rules = [r for r in rules if context['role'] in r.get('applies_to', [])]

        # Filter by category if specified
        if 'category' in context:
            rules = [r for r in rules if r.get('category') == context['category']]

        return rules

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
            return checkers.check_validator_approval(task, rule)

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


__all__ = [
    "RulesEngine",
]
