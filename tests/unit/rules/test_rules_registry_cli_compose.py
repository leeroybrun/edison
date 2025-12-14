from __future__ import annotations

from pathlib import Path

from edison.core.rules import RulesRegistry


def test_rules_registry_compose_cli_rules_includes_core_cli_rules(isolated_project_env: Path) -> None:
    registry = RulesRegistry(project_root=isolated_project_env)
    composed = registry.compose_cli_rules(packs=[])

    assert isinstance(composed, dict)
    rules = composed.get("rules")
    assert isinstance(rules, dict)
    assert "RULE.DELEGATION.PRIORITY_CHAIN" in rules

    # All entries returned by compose_cli_rules should have a cli config.
    for rule in rules.values():
        assert isinstance(rule, dict)
        assert isinstance(rule.get("cli"), dict)

