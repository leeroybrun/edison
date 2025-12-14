from __future__ import annotations

from pathlib import Path

from edison.core.rules import RulesRegistry


def test_compose_cli_rules_for_command_filters_to_relevant_rules(isolated_project_env: Path) -> None:
    registry = RulesRegistry(project_root=isolated_project_env)

    # Known core rule with cli.commands includes "task claim"
    composed = registry.compose_cli_rules_for_command(
        packs=[],
        command_name="task claim",
        resolve_sources=False,
    )
    rules = composed.get("rules")
    assert isinstance(rules, dict)
    assert "RULE.DELEGATION.PRIORITY_CHAIN" in rules

    # A command with no core cli rules should return empty.
    composed_none = registry.compose_cli_rules_for_command(
        packs=[],
        command_name="task list",
        resolve_sources=False,
    )
    rules_none = composed_none.get("rules")
    assert isinstance(rules_none, dict)
    assert rules_none == {}


