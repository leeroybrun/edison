"""Tests for non-interactive safety rule in registry.yml.

RED phase: These tests define the expected behavior for the non-interactive
safety rule that should be added to the Edison rules registry.

Task 045 requirement: Add Edison rule for non-interactive safety.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestNonInteractiveRule:
    """Test that rules registry includes non-interactive safety rule."""

    def test_registry_has_non_interactive_rule(self) -> None:
        """registry.yml should have a rule for non-interactive safety."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        rule_ids = [r.get("id") for r in rules]

        # Should have a non-interactive execution rule
        non_interactive_rules = [
            rid for rid in rule_ids
            if rid and ("NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper())
        ]
        assert len(non_interactive_rules) >= 1, (
            "registry.yml should have a non-interactive safety rule"
        )

    def test_non_interactive_rule_has_required_fields(self) -> None:
        """Non-interactive rule should have all required fields."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        non_interactive_rule = None
        for rule in rules:
            rid = rule.get("id", "")
            if "NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper():
                non_interactive_rule = rule
                break

        assert non_interactive_rule is not None, "Non-interactive rule not found"

        required_fields = ["id", "title", "category", "guidance"]
        for field in required_fields:
            assert field in non_interactive_rule, (
                f"Non-interactive rule should have '{field}' field"
            )

    def test_non_interactive_rule_applies_to_agents(self) -> None:
        """Non-interactive rule should apply to agents."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        non_interactive_rule = None
        for rule in rules:
            rid = rule.get("id", "")
            if "NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper():
                non_interactive_rule = rule
                break

        assert non_interactive_rule is not None, "Non-interactive rule not found"
        applies_to = non_interactive_rule.get("applies_to", [])
        assert "agent" in applies_to, (
            "Non-interactive rule should apply to 'agent'"
        )

    def test_non_interactive_rule_category_is_execution(self) -> None:
        """Non-interactive rule should have 'execution' category."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        non_interactive_rule = None
        for rule in rules:
            rid = rule.get("id", "")
            if "NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper():
                non_interactive_rule = rule
                break

        assert non_interactive_rule is not None, "Non-interactive rule not found"
        category = non_interactive_rule.get("category", "")
        assert category == "execution", (
            "Non-interactive rule category should be 'execution'"
        )

    def test_non_interactive_rule_guidance_mentions_commands(self) -> None:
        """Non-interactive rule guidance should mention interactive commands."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        non_interactive_rule = None
        for rule in rules:
            rid = rule.get("id", "")
            if "NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper():
                non_interactive_rule = rule
                break

        assert non_interactive_rule is not None, "Non-interactive rule not found"
        guidance = non_interactive_rule.get("guidance", "").lower()
        # Should mention interactive commands
        assert "interactive" in guidance or "vim" in guidance or "pager" in guidance, (
            "Guidance should mention interactive commands or pagers"
        )

    def test_non_interactive_rule_guidance_mentions_env_vars(self) -> None:
        """Non-interactive rule guidance should mention environment variables."""
        import yaml

        from edison.data import get_data_path

        registry_path = Path(get_data_path("rules")) / "registry.yml"
        with registry_path.open() as f:
            data = yaml.safe_load(f)

        rules = data.get("rules", [])
        non_interactive_rule = None
        for rule in rules:
            rid = rule.get("id", "")
            if "NONINTERACTIVE" in rid.upper() or "NON_INTERACTIVE" in rid.upper():
                non_interactive_rule = rule
                break

        assert non_interactive_rule is not None, "Non-interactive rule not found"
        guidance = non_interactive_rule.get("guidance", "").lower()
        # Should mention environment variables or CI/pager settings
        assert "ci" in guidance or "pager" in guidance or "environment" in guidance, (
            "Guidance should mention environment variables or non-interactive settings"
        )
