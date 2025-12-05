"""
Rules Engine for the Edison Rules system.

This module provides the RulesEngine class for enforcing per-project rules
based on task state and type. Rules are loaded from the composition system
(core → packs → project) via RulesRegistry.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.paths import get_management_paths
from edison.core.utils.subprocess import run_with_timeout

from .models import Rule, RuleViolation
from .errors import RuleViolationError
from . import checkers


class RulesEngine:
    """
    Enforces per-project rules based on task state and type.

    Rules are loaded from the full composition system (core → packs → project)
    via RulesRegistry. The config only controls enforcement settings, not rule
    definitions.

    Features:
    - Composed rules from registry (core + packs + project overlays)
    - Dynamic rules lookup API for transitions and commands
    - CLI display configuration for contextual guidance
    """

    def __init__(self, config: Dict[str, Any], packs: Optional[List[str]] = None):
        """
        Initialize rules engine from config.

        Args:
            config: Full Edison config (from ConfigManager().load_config())
            packs: Optional list of active packs (defaults to config-based detection)
        """
        self.rules_config = config.get("rules", {}) if isinstance(config, dict) else {}
        self.enforcement_enabled = self.rules_config.get("enforcement", True)

        # Load composed rules from registry (core → packs → project)
        from .registry import RulesRegistry
        self._registry = RulesRegistry()
        self._packs = packs or self._get_active_packs(config)
        composed = self._registry.compose(packs=self._packs)
        self._rules_map: Dict[str, Dict[str, Any]] = composed.get("rules", {})

        # Build state/type mappings from config (for backwards compatibility)
        # These map states/types to rule IDs that are then looked up from _rules_map
        self.rules_by_state = self._build_state_mappings()
        self.rules_by_type = self._build_type_mappings()
        self.project_rules = self._build_project_rules()

        # Lazy cache for context-aware rule lookup
        self._all_rules_cache: Optional[List[Rule]] = None

    def _get_active_packs(self, config: Dict[str, Any]) -> List[str]:
        """Get active packs from config."""
        packs_cfg = config.get("packs", {})
        if isinstance(packs_cfg, dict):
            return packs_cfg.get("active", []) or []
        return []

    def _build_state_mappings(self) -> Dict[str, List[Rule]]:
        """Build state-based rule mappings from config + composed rules."""
        raw = self.rules_config.get("byState", {})
        return self._build_rule_mapping(raw)

    def _build_type_mappings(self) -> Dict[str, List[Rule]]:
        """Build type-based rule mappings from config + composed rules."""
        raw = self.rules_config.get("byTaskType", {})
        return self._build_rule_mapping(raw)

    def _build_project_rules(self) -> List[Rule]:
        """Build project-wide rules from config + composed rules."""
        raw_list = self.rules_config.get("project", [])
        return self._parse_rule_list(raw_list)

    def _build_rule_mapping(self, raw: Dict[str, List[Dict]]) -> Dict[str, List[Rule]]:
        """Build rule mapping from raw config, enriching from composed rules."""
        parsed: Dict[str, List[Rule]] = {}
        for key, rule_list in (raw or {}).items():
            parsed[key] = self._parse_rule_list(rule_list or [])
        return parsed

    def _parse_rule_list(self, rule_list: List[Dict]) -> List[Rule]:
        """Parse list of rule dicts into Rule objects, enriching from composed rules."""
        rules = []
        for rule_dict in (rule_list or []):
            rule_id = rule_dict.get("id", "")
            # Enrich with composed rule content if available
            composed = self._rules_map.get(rule_id, {})
            enriched = {
                "id": rule_id,
                "description": rule_dict.get("description", composed.get("title", "")),
                "enforced": rule_dict.get("enforced", True),
                "blocking": rule_dict.get("blocking", composed.get("blocking", False)),
                "reference": rule_dict.get("reference"),
                "config": rule_dict.get("config"),
                "title": composed.get("title"),
                "content": composed.get("body"),
                "category": composed.get("category"),
                "contexts": composed.get("contexts", []),
                "cli": composed.get("cli"),
            }
            rules.append(Rule(**enriched))
        return rules

    # =========================================================================
    # Dynamic Rules API (for session/next and CLI)
    # =========================================================================

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a single composed rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Composed rule dict or None if not found
        """
        return self._rules_map.get(rule_id)

    def get_all_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get all composed rules.
        
        Returns:
            Dict mapping rule ID to composed rule dict
        """
        return dict(self._rules_map)

    def get_rules_for_transition(
        self,
        domain: str,
        from_state: str,
        to_state: str,
    ) -> List[Dict[str, Any]]:
        """Get rules for a state transition.
        
        Args:
            domain: State machine domain (task, qa, etc.)
            from_state: Source state
            to_state: Target state
            
        Returns:
            List of composed rule dicts applicable to this transition
        """
        rule_ids = self._get_transition_rule_ids(domain, from_state, to_state)
        return [self._rules_map[rid] for rid in rule_ids if rid in self._rules_map]

    def _get_transition_rule_ids(self, domain: str, from_state: str, to_state: str) -> List[str]:
        """Get rule IDs for a transition from state machine config.
        
        This reads from config's rules.transitions section if defined.
        """
        transitions_cfg = self.rules_config.get("transitions", {})
        domain_cfg = transitions_cfg.get(domain, {})
        transition_key = f"{from_state}->{to_state}"
        return domain_cfg.get(transition_key, []) or []

    def get_rules_for_command(
        self,
        command: str,
        timing: str = "before",
    ) -> List[Dict[str, Any]]:
        """Get rules to display for a CLI command.
        
        Args:
            command: CLI command name (e.g., "task claim", "qa promote")
            timing: When to display - "before", "after", or "both"
            
        Returns:
            List of composed rule dicts that should be displayed
        """
        return [
            rule for rule in self._rules_map.values()
            if self._rule_matches_command(rule, command, timing)
        ]

    def _rule_matches_command(self, rule: Dict[str, Any], command: str, timing: str) -> bool:
        """Check if rule should be shown for command at given timing."""
        cli_config = rule.get("cli", {}) or {}
        commands = cli_config.get("commands", []) or []
        rule_timing = cli_config.get("timing", "before")
        
        if not commands:
            return False
        if command not in commands and "*" not in commands:
            return False
        if timing != "both" and rule_timing != "both" and rule_timing != timing:
            return False
        return True

    def get_rules_by_context(self, context_type: str) -> List[Dict[str, Any]]:
        """Get rules matching a context type.
        
        Args:
            context_type: Context type (guidance, delegation, validation, etc.)
            
        Returns:
            List of composed rule dicts matching the context
        """
        return [
            rule for rule in self._rules_map.values()
            if context_type in (rule.get("contexts") or [])
        ]

    def expand_rule_ids(self, rule_ids: List[str]) -> List[Dict[str, Any]]:
        """Expand rule IDs to full rule objects.
        
        Args:
            rule_ids: List of rule IDs to expand
            
        Returns:
            List of rule info dicts
        """
        return [
            {
                "id": rid,
                "title": self._rules_map[rid].get("title", rid),
                "content": self._rules_map[rid].get("body", ""),
                "blocking": self._rules_map[rid].get("blocking", False),
            }
            for rid in rule_ids if rid in self._rules_map
        ]

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
    # State machine guard helpers (unified with state module)
    # ------------------------------------------------------------------
    def check_transition_guards(
        self,
        from_state: str,
        to_state: str,
        task: Dict[str, Any],
        session: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
        entity_type: str = "task",
    ) -> Tuple[bool, Optional[str]]:
        """
        Check guard conditions for a state transition.

        Delegates to the unified state machine guard system. Guards are
        loaded from data/guards/ with layered composition (core → packs → project).

        Args:
            from_state: Current state
            to_state: Target state
            task: Task dict with metadata
            session: Session dict (optional)
            validation_results: Validation results dict (optional)
            entity_type: Entity type for transition (default: 'task')

        Returns:
            Tuple of (allowed: bool, error_message: Optional[str])
        """
        from edison.core.state import validate_transition
        
        # Build context for guards
        context = {
            "task": task,
            "session": session or {},
            "validation_results": validation_results or {},
            "entity_type": entity_type,
            "from_state": from_state,
            "to_state": to_state,
        }
        
        # Delegate to unified state machine
        valid, error = validate_transition(
            entity_type=entity_type,
            from_state=from_state,
            to_state=to_state,
            context=context,
        )
        
        return valid, error if not valid else None

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
        Check if task satisfies a rule using the checker registry.

        Args:
            task: Task object
            rule: Rule to check

        Returns:
            True if rule is satisfied, False otherwise
        """
        # Use registry-based dispatch instead of hardcoded if-else
        checker = checkers.get_checker(rule.id)

        if checker is not None:
            return checker(task, rule)

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
