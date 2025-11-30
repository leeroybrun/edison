"""Tests for role-based rule filtering API (T-005).

These tests verify the APIs for loading and filtering rules by role
from the bundled registry data.

Note: The role-based APIs have been moved from RulesEngine to
edison.core.composition.registries.rules for architectural coherence.
They are still accessible via edison.core.rules for convenience.
"""
from __future__ import annotations

import pytest

from edison.core.rules import (
    load_bundled_rules,
    get_rules_for_role,
    filter_rules,
)


def test_get_all_returns_all_rules_from_registry() -> None:
    """load_bundled_rules() should load all 37 rules from the bundled registry."""
    rules = load_bundled_rules()

    # T-003 added applies_to to all 37 rules
    assert len(rules) >= 37, "Expected at least 37 rules in registry"

    # Verify structure - each rule should be a dict with required fields
    for rule in rules:
        assert isinstance(rule, dict)
        assert "id" in rule
        assert "applies_to" in rule
        assert isinstance(rule["applies_to"], list)


def test_get_rules_for_role_orchestrator() -> None:
    """get_rules_for_role('orchestrator') should return only orchestrator rules."""
    rules = get_rules_for_role("orchestrator")

    # All returned rules must include 'orchestrator' in applies_to
    for rule in rules:
        assert "orchestrator" in rule["applies_to"], \
            f"Rule {rule['id']} does not apply to orchestrator"

    # Should have at least some orchestrator rules
    assert len(rules) > 0, "Expected at least one orchestrator rule"


def test_get_rules_for_role_agent() -> None:
    """get_rules_for_role('agent') should return only agent rules."""
    rules = get_rules_for_role("agent")

    # All returned rules must include 'agent' in applies_to
    for rule in rules:
        assert "agent" in rule["applies_to"], \
            f"Rule {rule['id']} does not apply to agent"

    # Should have at least some agent rules
    assert len(rules) > 0, "Expected at least one agent rule"


def test_get_rules_for_role_validator() -> None:
    """get_rules_for_role('validator') should return only validator rules."""
    rules = get_rules_for_role("validator")

    # All returned rules must include 'validator' in applies_to
    for rule in rules:
        assert "validator" in rule["applies_to"], \
            f"Rule {rule['id']} does not apply to validator"

    # Should have at least some validator rules
    assert len(rules) > 0, "Expected at least one validator rule"


def test_get_rules_for_role_invalid_role_raises_error() -> None:
    """get_rules_for_role() should raise ValueError for invalid roles."""
    with pytest.raises(ValueError, match="Invalid role.*Must be orchestrator, agent, or validator"):
        get_rules_for_role("invalid_role")

    with pytest.raises(ValueError, match="Invalid role.*Must be orchestrator, agent, or validator"):
        get_rules_for_role("admin")

    with pytest.raises(ValueError, match="Invalid role.*Must be orchestrator, agent, or validator"):
        get_rules_for_role("")


def test_filter_rules_by_role() -> None:
    """filter_rules() should support role filtering."""
    # Get agent-specific rules via context
    rules = filter_rules({"role": "agent"})

    # All returned rules must include 'agent' in applies_to
    for rule in rules:
        assert "agent" in rule["applies_to"], \
            f"Rule {rule['id']} does not apply to agent"

    # Should have at least some agent rules
    assert len(rules) > 0, "Expected at least one agent rule"


def test_filter_rules_with_role_and_category() -> None:
    """filter_rules() should support combining role and category filters."""
    # Get validation rules for orchestrator
    rules = filter_rules({
        "role": "orchestrator",
        "category": "validation"
    })

    # All returned rules must match both filters
    for rule in rules:
        assert "orchestrator" in rule["applies_to"], \
            f"Rule {rule['id']} does not apply to orchestrator"
        assert rule.get("category") == "validation", \
            f"Rule {rule['id']} is not in validation category"


def test_filter_rules_empty_dict_returns_all() -> None:
    """filter_rules({}) with no filters should return all rules."""
    rules = filter_rules({})

    # Should return all rules when no filters specified
    all_rules = load_bundled_rules()
    assert len(rules) == len(all_rules)


def test_rules_have_expected_structure() -> None:
    """Verify that loaded rules have the expected data structure."""
    rules = load_bundled_rules()

    # Sample a few rules to verify structure
    for rule in rules[:5]:
        # Required fields from registry.yml
        assert "id" in rule
        assert "title" in rule
        assert "category" in rule
        assert "blocking" in rule
        assert "applies_to" in rule
        assert "sourcePath" in rule
        assert "guidance" in rule

        # Type checks
        assert isinstance(rule["id"], str)
        assert isinstance(rule["title"], str)
        assert isinstance(rule["category"], str)
        assert isinstance(rule["blocking"], bool)
        assert isinstance(rule["applies_to"], list)
        assert isinstance(rule["sourcePath"], str)
        assert isinstance(rule["guidance"], str)
