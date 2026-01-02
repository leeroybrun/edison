"""Pal discovery mixin for role-specific guidelines and rules.

This module provides PalDiscoveryMixin which handles discovering
applicable guidelines and rules for different Pal roles.

Uses unified patterns module for fnmatch operations.
"""
from __future__ import annotations
from typing import List, Dict, Any, Set, TYPE_CHECKING

from edison.core.utils.patterns import matches_any_pattern

if TYPE_CHECKING:
    from .adapter import PalAdapter


def _canonical_role(role: str) -> str:
    """Normalize logical role names for filtering.

    Examples:
      - "default" → "default"
      - "codereviewer" / "code-reviewer" / "project-code-reviewer" → "codereviewer"
      - "planner" / "project-planner" → "planner"
      - Any other "project-*" → "project"
    """
    raw = (role or "").strip()
    low = raw.lower()

    if low.startswith("project-"):
        base = low[len("project-") :]
        if base in {"codereviewer", "code-reviewer"}:
            return "codereviewer"
        if base == "planner":
            return "planner"
        return "project"

    if low in {"codereviewer", "code-reviewer"}:
        return "codereviewer"
    if low == "planner":
        return "planner"
    if low == "default" or not low:
        return "default"

    return low


class PalDiscoveryMixin:
    """Mixin for discovering role-specific guidelines and rules."""

    def get_applicable_guidelines(self: PalAdapter, role: str) -> List[str]:
        """Return guideline names applicable to a logical role.

        Role mapping reference:
          - default: All guidelines
          - codereviewer: Quality, security, performance, review-focused
          - planner: Architecture / design oriented
          - project-*: Project overlays + pack guidelines

        Args:
            role: Pal role identifier

        Returns:
            List of applicable guideline names
        """
        packs = self.get_active_packs()
        role_spec = self._get_role_spec(role)

        # Role-specific pack selection: intersect configured packs with active packs.
        effective_packs = packs
        if role_spec is not None and isinstance(role_spec.get("packs"), list):
            requested_packs = [str(p).strip() for p in role_spec.get("packs", []) if str(p).strip()]
            if requested_packs:
                effective_packs = [p for p in packs if p in requested_packs]
                if not effective_packs:
                    # Fallback to all active packs when intersection is empty.
                    effective_packs = packs

        all_names = self.guideline_registry.all_names(effective_packs, include_project=True)

        # Config-driven guideline patterns (wildcards + substrings)
        if role_spec is not None and isinstance(role_spec.get("guidelines"), list):
            patterns = [str(p).strip().lower() for p in role_spec.get("guidelines", []) if str(p).strip()]
            if patterns:
                selected: List[str] = []
                for name in all_names:
                    lower = name.lower()
                    # Check for glob pattern match OR substring match
                    if matches_any_pattern(lower, patterns) or any(pat in lower for pat in patterns):
                        selected.append(name)
                return selected

        canonical = _canonical_role(role)

        if canonical == "default":
            return all_names

        if canonical == "codereviewer":
            review_keywords = {"quality", "security", "performance", "review"}
            selected = []
            for name in all_names:
                lower = name.lower()
                if any(keyword in lower for keyword in review_keywords):
                    selected.append(name)
            return selected

        if canonical == "planner":
            planner_keywords = {"architecture", "design", "planning"}
            selected = []
            for name in all_names:
                lower = name.lower()
                if any(keyword in lower for keyword in planner_keywords):
                    selected.append(name)
            return selected

        if canonical == "project":
            # Project overlays + pack guidelines only (skip core-only guidelines)
            selected = []
            for name in all_names:
                has_project = self.guideline_registry.project_override_path(name) is not None
                has_pack = bool(self.guideline_registry.pack_paths(name, effective_packs))
                if has_project or has_pack:
                    selected.append(name)
            return selected

        # Fallback: return everything for unknown roles
        return all_names

    def get_applicable_rules(self: PalAdapter, role: str) -> List[Dict[str, Any]]:
        """Return composed rules applicable to a logical role.

        Args:
            role: Pal role identifier

        Returns:
            List of applicable rule dictionaries
        """
        packs = self.get_active_packs()

        composed = self.rules_registry.compose(packs=packs)
        rules_map: Dict[str, Dict[str, Any]] = composed.get("rules", {}) or {}
        role_spec = self._get_role_spec(role)
        canonical = _canonical_role(role)

        ids_by_category: Dict[str, Set[str]] = {}
        ids_by_origin: Dict[str, Dict[str, Set[str]]] = {}

        def _origin_bucket(origin: str) -> str:
            raw = (origin or "").strip()
            if raw.startswith("pack:"):
                return raw.split(":", 1)[1]
            return raw or "unknown"

        for rid, rule in rules_map.items():
            if not isinstance(rule, dict):
                continue
            category = str(rule.get("category") or "").strip().lower()
            if not category:
                continue
            ids_by_category.setdefault(category, set()).add(rid)

            origins = rule.get("origins") or []
            if not isinstance(origins, list) or not origins:
                origins = ["unknown"]
            for o in origins:
                bucket = _origin_bucket(str(o))
                ids_by_origin.setdefault(bucket, {}).setdefault(category, set()).add(rid)

        # Config-driven rule category + pack filtering
        if role_spec is not None and isinstance(role_spec.get("rules"), list):
            categories = {str(c).strip().lower() for c in role_spec.get("rules", []) if str(c).strip()}
            packs_filter: List[str] = []
            if isinstance(role_spec.get("packs"), list):
                packs_filter = [str(p).strip() for p in role_spec.get("packs", []) if str(p).strip()]

            selected_ids: Set[str] = set()
            for category in categories:
                if packs_filter:
                    # Always include project/user rules, core rules, plus rules from configured packs.
                    selected_ids.update(ids_by_origin.get("project", {}).get(category, set()))
                    selected_ids.update(ids_by_origin.get("user", {}).get(category, set()))
                    selected_ids.update(ids_by_origin.get("core", {}).get(category, set()))
                    for pack_name in packs_filter:
                        selected_ids.update(ids_by_origin.get(pack_name, {}).get(category, set()))
                else:
                    selected_ids.update(ids_by_category.get(category, set()))

            return [rules_map[rid] for rid in selected_ids if rid in rules_map]

        # Default/unknown roles see the full composed view.
        if canonical in {"default", "project"}:
            return list(rules_map.values())

        if canonical == "codereviewer":
            include_categories = {"validation", "implementation", "context", "general"}
        elif canonical == "planner":
            include_categories = {"delegation", "session", "transition", "context"}
        else:
            # Fallback: no additional filtering
            return list(rules_map.values())

        selected_ids: Set[str] = set()
        for category in include_categories:
            selected_ids.update(ids_by_category.get(category, set()))

        return [rules_map[rid] for rid in selected_ids if rid in rules_map]


__all__ = ["PalDiscoveryMixin", "_canonical_role"]
