"""Rules registry public surface.

This is a subpackage (not a pile of `registry_*.py` files) so that the registry
implementation can be split into focused modules without prefix spam.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import RulesRegistryBase
from .query import RulesRegistryQueryMixin


class RulesRegistry(RulesRegistryQueryMixin, RulesRegistryBase):
    """Load and compose rules from bundled + pack YAML registries."""

    pass


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


# ------------------------------------------------------------------
# Role-based rule query API (uses composition system)
# ------------------------------------------------------------------
def get_rules_for_role(role: str, packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get composed rules that apply to a specific role.

    Uses RulesRegistry.compose() to get fully composed rules with:
    - Pack overlays
    - Project overlays
    - Include resolution

    Args:
        role: One of 'orchestrator', 'agent', 'validator'
        packs: Optional list of active packs (defaults to empty)

    Returns:
        List of composed rule dictionaries where applies_to includes the role

    Raises:
        ValueError: If role is not one of the valid options
    """
    if role not in ('orchestrator', 'agent', 'validator'):
        raise ValueError(f"Invalid role: {role}. Must be orchestrator, agent, or validator")

    # Use composition system for full rule resolution
    registry = RulesRegistry()
    composed = registry.compose(packs=packs or [])
    rules_map = composed.get("rules", {})
    
    # Filter by role from composed rules
    return [
        rule for rule in rules_map.values()
        if role in (rule.get('applies_to') or [])
    ]


def filter_rules(context: Dict[str, Any], packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Filter composed rules by context metadata (role, category, etc.).

    Uses RulesRegistry.compose() for full rule resolution.

    Args:
        context: Dictionary with optional keys:
            - role: One of 'orchestrator', 'agent', 'validator'
            - category: Rule category (e.g., 'validation', 'delegation')
        packs: Optional list of active packs (defaults to empty)

    Returns:
        List of composed rule dictionaries matching the context filters
    """
    # Use composition system for full rule resolution
    registry = RulesRegistry()
    composed = registry.compose(packs=packs or [])
    rules = list(composed.get("rules", {}).values())

    # Filter by role if specified
    if 'role' in context:
        rules = [r for r in rules if context['role'] in (r.get('applies_to') or [])]

    # Filter by category if specified
    if 'category' in context:
        rules = [r for r in rules if r.get('category') == context['category']]

    return rules


__all__ = [
    "RulesRegistry",
    "compose_rules",
    "get_rules_for_role",
    "filter_rules",
]
