"""
Rule checking and formatting for CLI consumption.

This module provides business logic for checking and formatting rules
that are applicable to specific contexts or transitions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .engine import RulesEngine
from .models import Rule


def get_rules_for_context_formatted(
    engine: RulesEngine,
    contexts: Optional[List[str]] = None,
    transition: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get formatted rules for given contexts.

    Args:
        engine: RulesEngine instance
        contexts: List of rule contexts to check
        transition: State transition to check (e.g., 'wip->done')
        task_id: Task ID for context-aware rule checking

    Returns:
        Dictionary with:
        - rules: List of applicable rule dictionaries
        - count: Number of rules
        - contexts: List of contexts checked
    """
    applicable_rules = []
    contexts_checked = contexts or []

    # Transition-based rule lookup (from config-driven transition mappings).
    if transition:
        from_state, sep, to_state = str(transition).partition("->")
        if sep and from_state.strip() and to_state.strip():
            # Currently task transitions only (CLI syntax does not include domain).
            rules = engine.get_rules_for_transition("task", from_state.strip(), to_state.strip())
            for rule in rules:
                applicable_rules.append(
                    {
                        "id": rule.get("id") or "",
                        "description": rule.get("title") or rule.get("id") or "",
                        "blocking": bool(rule.get("blocking", False)),
                        "enforced": True,
                        "contexts": rule.get("contexts", []) or [],
                        "priority": "normal",
                    }
                )
        contexts_checked = contexts_checked or []

    if contexts:
        for ctx in contexts:
            # Preserve the feature: if rules use filePatterns, allow the engine to
            # auto-detect changed files (git status / session diff) when needed.
            rules = engine.get_rules_for_context(ctx)
            for rule in rules:
                rule_dict = {
                    "id": rule.id,
                    "description": rule.description,
                    "blocking": rule.blocking,
                    "enforced": rule.enforced,
                    "contexts": (rule.config or {}).get("contexts", []),
                    "priority": (rule.config or {}).get("priority", "normal"),
                }
                # Avoid duplicates
                if rule_dict not in applicable_rules:
                    applicable_rules.append(rule_dict)

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    applicable_rules.sort(key=lambda r: priority_order.get(r.get("priority", "normal"), 2))

    return {
        "rules": applicable_rules,
        "count": len(applicable_rules),
        "contexts": contexts_checked,
    }


def format_rules_output(
    rules_data: Dict[str, Any],
    format_mode: str = "short",
) -> str:
    """Format rules data for display.

    Args:
        rules_data: Dictionary from get_rules_for_context_formatted
        format_mode: One of 'short', 'full', 'markdown'

    Returns:
        Formatted string output
    """
    rules = rules_data.get("rules", [])
    count = rules_data.get("count", 0)

    if format_mode == "full":
        lines = [f"Applicable rules ({count}):"]
        lines.append("")
        for rule in rules:
            lines.append(f"RULE.{rule['id'].upper()}")
            lines.append(f"  Priority: {rule.get('priority', 'normal')}")
            lines.append(f"  Contexts: {', '.join([str(c) for c in rule.get('contexts', [])])}")
            if rule.get("content"):
                lines.append(f"  Content:\n    {rule['content'][:300]}...")
            lines.append("")
        return "\n".join(lines)

    elif format_mode == "markdown":
        lines = ["# Applicable Rules"]
        lines.append("")
        for rule in rules:
            lines.append(f"## RULE.{rule['id'].upper()}")
            lines.append(f"**Priority**: {rule.get('priority', 'normal')}")
            lines.append(f"**Contexts**: {', '.join([str(c) for c in rule.get('contexts', [])])}")
            if rule.get("content"):
                lines.append(f"\n{rule['content']}\n")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    else:  # short format
        if rules:
            lines = [f"Applicable rules ({count}):"]
            for rule in rules:
                priority = rule.get('priority', 'normal')
                priority_marker = "🔴" if priority == "critical" else "🟡" if priority == "high" else "⚪"
                lines.append(f"  {priority_marker} RULE.{rule['id'].upper()}")
            return "\n".join(lines)
        else:
            return "No applicable rules found."


__all__ = [
    "get_rules_for_context_formatted",
    "format_rules_output",
]
