"""Context-aware rule selection for RulesEngine.

This module exists to keep `engine.py` small and focused while still exposing a
single public `RulesEngine` class.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.utils.patterns import matches_any_pattern
from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.profiling import span

from .models import Rule


class RulesContextMixin:
    """Context-aware helpers used by RulesEngine."""

    def get_rules_by_context(self, context_type: str) -> List[Dict[str, Any]]:
        """Get rules matching a context type."""
        return [
            rule
            for rule in self._rules_map.values()
            if context_type in (rule.get("contexts") or [])
        ]

    def expand_rule_ids(self, rule_ids: List[str]) -> List[Dict[str, Any]]:
        """Expand rule IDs to full rule objects."""
        out: List[Dict[str, Any]] = []
        for rid in rule_ids:
            if rid not in self._rules_map:
                continue
            self._ensure_rule_body(rid)
            out.append(
                {
                    "id": rid,
                    "title": self._rules_map[rid].get("title", rid),
                    "content": self._rules_map[rid].get("body", ""),
                    "blocking": self._rules_map[rid].get("blocking", False),
                }
            )
        return out

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

    def _get_context_index(self) -> Dict[str, List[Tuple[int, str, Rule, Dict[str, Any]]]]:
        """Build (lazily) an index from context_type -> candidate rule entries.

        This avoids scanning all rules for every context query, which becomes
        expensive in large projects.
        """
        if self._context_index is not None:
            return self._context_index

        with span("rules.engine.context_index.build"):
            index: Dict[str, List[Tuple[int, str, Rule, Dict[str, Any]]]] = {}
            for rule in self._iter_all_rules():
                cfg = rule.config or {}
                ctx_entries = cfg.get("contexts") or []
                if not isinstance(ctx_entries, list):
                    continue
                for entry in ctx_entries:
                    if not isinstance(entry, dict):
                        continue
                    entry_type = str(entry.get("type") or "").strip().lower()
                    if not entry_type:
                        continue
                    priority = int(entry.get("priority") or cfg.get("priority") or 100)
                    index.setdefault(entry_type, []).append((priority, rule.id, rule, entry))

            for key, items in index.items():
                items.sort(key=lambda t: (t[0], t[1]))

            self._context_index = index
            return index

    def _get_changed_files(self) -> List[str]:
        """Get changed files using FileContextService."""
        try:
            from edison.core.context.files import FileContextService

            svc = FileContextService()
            ctx = svc.get_current()
            return ctx.all_files
        except Exception:
            return []

    def get_rules_for_context(
        self,
        context_type: str,
        task_state: Optional[str] = None,
        changed_files: Optional[List[Path]] = None,
        operation: Optional[str] = None,
    ) -> List[Rule]:
        """Return applicable rules for a given runtime context."""
        ctx = (context_type or "").strip().lower()
        if not ctx:
            return []

        # Normalise changed_files to repo-relative strings when possible.
        # IMPORTANT:
        # - `changed_files=None` means "auto-detect when needed".
        # - An explicit empty list means "no changed files" (do NOT auto-detect).
        rel_paths: Optional[List[str]] = [] if changed_files is not None else None
        if changed_files is not None:
            try:
                root = PathResolver.resolve_project_root()
            except EdisonPathError:
                root = None
            rel_paths = []
            for p in changed_files:
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

        index = self._get_context_index()
        bucket = index.get(ctx, [])

        for priority, rule_id, rule, entry in bucket:
            states = entry.get("states")
            if task_state_norm and isinstance(states, list):
                states_norm = {str(s).strip().lower() for s in states}
                if task_state_norm not in states_norm:
                    continue

            ops = entry.get("operations")
            if op_norm and isinstance(ops, list) and ops:
                ops_norm = {str(o).strip() for o in ops}
                if op_norm not in ops_norm:
                    continue

            patterns = entry.get("filePatterns") or []
            if patterns:
                if rel_paths is None:
                    rel_paths = self._get_changed_files()
                if not rel_paths:
                    continue
                pat_list = [str(pat) for pat in patterns]
                if not any(matches_any_pattern(path, pat_list) for path in rel_paths):
                    continue

            candidates.append((priority, rule_id, rule))

        if not candidates and ctx == "guidance":
            for rule in self.project_rules or []:
                if rule.blocking:
                    continue
                priority = int((rule.config or {}).get("priority", 100))
                candidates.append((priority, rule.id, rule))

        candidates.sort(key=lambda t: (t[0], t[1]))
        return [r for _, _, r in candidates]


__all__ = ["RulesContextMixin"]
