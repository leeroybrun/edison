"""Tests for validation policy models.

RED phase: These tests define the expected behavior of ValidationPreset
and ValidationPolicy data structures used for config-driven validation.
"""
from __future__ import annotations

import pytest


@pytest.mark.qa
class TestValidationPreset:
    """Tests for ValidationPreset dataclass."""

    def test_preset_has_required_attributes(self):
        """ValidationPreset must have validators, evidence, and blocking flags."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            name="quick",
            validators=["global-codex"],
            required_evidence=["implementation-report.md"],
            blocking_validators=["global-codex"],
        )

        assert preset.name == "quick"
        assert preset.validators == ["global-codex"]
        assert preset.required_evidence == ["implementation-report.md"]
        assert preset.blocking_validators == ["global-codex"]

    def test_preset_defaults_blocking_to_all_validators(self):
        """If blocking_validators not provided, defaults to all validators."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            name="quick",
            validators=["global-codex", "security"],
            required_evidence=["implementation-report.md"],
        )

        # Should default to all validators being blocking
        assert preset.blocking_validators == ["global-codex", "security"]

    def test_preset_has_optional_description(self):
        """ValidationPreset can have an optional description."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            name="quick",
            validators=["global-codex"],
            required_evidence=["implementation-report.md"],
            description="Minimal validation for docs-only tasks",
        )

        assert preset.description == "Minimal validation for docs-only tasks"

    def test_preset_can_specify_empty_evidence_list(self):
        """Preset with empty required evidence is valid (advisory-only)."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            name="advisory",
            validators=["coderabbit"],
            required_evidence=[],
            blocking_validators=[],
        )

        assert preset.required_evidence == []
        assert preset.blocking_validators == []


@pytest.mark.qa
class TestValidationPolicy:
    """Tests for ValidationPolicy resolved result."""

    def test_policy_contains_preset_and_context(self):
        """ValidationPolicy contains the resolved preset and task context."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            name="quick",
            validators=["global-codex"],
            required_evidence=["implementation-report.md"],
        )

        policy = ValidationPolicy(
            preset=preset,
            task_id="T001",
            changed_files=["docs/README.md"],
            inferred_preset_name="quick",
        )

        assert policy.preset.name == "quick"
        assert policy.task_id == "T001"
        assert policy.changed_files == ["docs/README.md"]
        assert policy.inferred_preset_name == "quick"

    def test_policy_blocking_validators_property(self):
        """ValidationPolicy.blocking_validators returns preset's blocking validators."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            name="quick",
            validators=["global-codex", "security"],
            required_evidence=["implementation-report.md"],
            blocking_validators=["global-codex"],
        )

        policy = ValidationPolicy(
            preset=preset,
            task_id="T001",
            changed_files=["src/app.py"],
            inferred_preset_name="quick",
        )

        assert policy.blocking_validators == ["global-codex"]

    def test_policy_required_evidence_property(self):
        """ValidationPolicy.required_evidence returns preset's required evidence."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            name="standard",
            validators=["global-codex"],
            required_evidence=["command-test.txt", "command-lint.txt"],
        )

        policy = ValidationPolicy(
            preset=preset,
            task_id="T001",
            changed_files=["src/app.py"],
            inferred_preset_name="standard",
        )

        assert policy.required_evidence == ["command-test.txt", "command-lint.txt"]

    def test_policy_has_was_escalated_flag(self):
        """ValidationPolicy tracks if preset was escalated from initial inference."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            name="standard",
            validators=["global-codex", "security"],
            required_evidence=["command-test.txt"],
        )

        # Policy where escalation occurred (inferred "quick" but escalated to "standard")
        policy = ValidationPolicy(
            preset=preset,
            task_id="T001",
            changed_files=["src/app.py"],
            inferred_preset_name="quick",
            was_escalated=True,
            escalation_reason="Code changes detected in src/",
        )

        assert policy.was_escalated is True
        assert policy.escalation_reason == "Code changes detected in src/"
