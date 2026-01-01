"""Tests for validation presets.

Tests the policy module which provides:
- Config-driven validation presets (quick, standard, comprehensive)
- Pack-extensible preset configuration
- Preset inference from task/file context
- Escalation rules (code changes escalate above quick)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestValidationPresetModel:
    """Test ValidationPreset dataclass."""

    def test_preset_has_required_fields(self) -> None:
        """ValidationPreset has id, name, validators, and evidence_required."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            id="quick",
            name="Quick Validation",
            validators=["global-codex"],
            evidence_required=[],
        )

        assert preset.id == "quick"
        assert preset.name == "Quick Validation"
        assert preset.validators == ["global-codex"]
        assert preset.evidence_required == []

    def test_preset_immutable(self) -> None:
        """ValidationPreset is immutable (frozen dataclass)."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            id="quick",
            name="Quick Validation",
            validators=["global-codex"],
            evidence_required=[],
        )

        with pytest.raises(AttributeError):
            preset.id = "modified"  # type: ignore[misc]

    def test_preset_to_dict(self) -> None:
        """ValidationPreset can be converted to dict."""
        from edison.core.qa.policy.models import ValidationPreset

        preset = ValidationPreset(
            id="standard",
            name="Standard Validation",
            validators=["global-codex", "global-claude"],
            evidence_required=["command-test.txt", "command-lint.txt"],
        )

        d = preset.to_dict()
        assert d["id"] == "standard"
        assert d["name"] == "Standard Validation"
        assert d["validators"] == ["global-codex", "global-claude"]
        assert d["evidence_required"] == ["command-test.txt", "command-lint.txt"]

    def test_preset_from_dict(self) -> None:
        """ValidationPreset can be created from dict."""
        from edison.core.qa.policy.models import ValidationPreset

        data = {
            "id": "comprehensive",
            "name": "Comprehensive Validation",
            "validators": ["global-codex", "global-claude", "security"],
            "evidence_required": ["command-test.txt", "command-lint.txt", "command-build.txt"],
        }

        preset = ValidationPreset.from_dict(data)
        assert preset.id == "comprehensive"
        assert preset.name == "Comprehensive Validation"
        assert preset.validators == ["global-codex", "global-claude", "security"]


class TestValidationPolicyModel:
    """Test ValidationPolicy dataclass."""

    def test_policy_has_preset_and_escalation(self) -> None:
        """ValidationPolicy wraps preset with escalation metadata."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            id="quick",
            name="Quick Validation",
            validators=["global-codex"],
            evidence_required=[],
        )

        policy = ValidationPolicy(
            preset=preset,
            escalated_from=None,
            escalation_reason=None,
        )

        assert policy.preset.id == "quick"
        assert policy.escalated_from is None
        assert policy.escalation_reason is None

    def test_policy_tracks_escalation(self) -> None:
        """ValidationPolicy tracks when preset was escalated."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        preset = ValidationPreset(
            id="standard",
            name="Standard Validation",
            validators=["global-codex", "global-claude"],
            evidence_required=["command-test.txt"],
        )

        policy = ValidationPolicy(
            preset=preset,
            escalated_from="quick",
            escalation_reason="Code changes detected",
        )

        assert policy.preset.id == "standard"
        assert policy.escalated_from == "quick"
        assert policy.escalation_reason == "Code changes detected"

    def test_policy_is_escalated_property(self) -> None:
        """ValidationPolicy.is_escalated returns True when escalated_from is set."""
        from edison.core.qa.policy.models import ValidationPolicy, ValidationPreset

        quick_preset = ValidationPreset(
            id="quick",
            name="Quick",
            validators=["global-codex"],
            evidence_required=[],
        )
        standard_preset = ValidationPreset(
            id="standard",
            name="Standard",
            validators=["global-codex", "global-claude"],
            evidence_required=["command-test.txt"],
        )

        not_escalated = ValidationPolicy(preset=quick_preset)
        escalated = ValidationPolicy(
            preset=standard_preset,
            escalated_from="quick",
            escalation_reason="Code changes",
        )

        assert not_escalated.is_escalated is False
        assert escalated.is_escalated is True


class TestPresetConfigLoader:
    """Test loading presets from YAML config."""

    def test_loads_presets_from_validators_yaml(self, tmp_path: Path) -> None:
        """PresetConfigLoader loads presets from validation.presets in config."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
    standard:
      name: "Standard Validation"
      validators:
        - global-codex
        - global-claude
      evidence_required:
        - command-test.txt
        - command-lint.txt
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        presets = loader.load_presets()

        assert "quick" in presets
        assert "standard" in presets
        assert presets["quick"].validators == ["global-codex"]
        assert presets["standard"].validators == ["global-codex", "global-claude"]

    def test_get_preset_by_id(self, tmp_path: Path) -> None:
        """PresetConfigLoader.get_preset returns specific preset."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        preset = loader.get_preset("quick")

        assert preset is not None
        assert preset.id == "quick"
        assert preset.name == "Quick Validation"

    def test_get_preset_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """PresetConfigLoader.get_preset returns None for unknown preset."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        preset = loader.get_preset("nonexistent")

        assert preset is None

    def test_default_preset_from_config(self, tmp_path: Path) -> None:
        """PresetConfigLoader reads default preset from config."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  defaults:
    preset: quick
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
    standard:
      name: "Standard Validation"
      validators:
        - global-codex
        - global-claude
      evidence_required:
        - command-test.txt
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        default = loader.get_default_preset_id()

        assert default == "quick"


class TestPresetInference:
    """Test inferring preset from task/file context."""

    def test_docs_only_changes_infer_quick(self, tmp_path: Path) -> None:
        """Tasks with only doc changes infer 'quick' preset."""
        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=tmp_path)
        files = ["README.md", "docs/guide.md", "CHANGELOG.md"]

        inferred = inference.infer_preset_from_files(files)

        assert inferred == "quick"

    def test_code_changes_infer_standard(self, tmp_path: Path) -> None:
        """Tasks with code changes infer 'standard' preset."""
        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=tmp_path)
        files = ["src/core/module.py", "tests/test_module.py"]

        inferred = inference.infer_preset_from_files(files)

        assert inferred == "standard"

    def test_mixed_files_escalate_to_standard(self, tmp_path: Path) -> None:
        """Tasks with docs + code changes escalate to 'standard'."""
        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=tmp_path)
        files = ["README.md", "src/core/module.py"]

        inferred = inference.infer_preset_from_files(files)

        assert inferred == "standard"

    def test_empty_files_uses_default(self, tmp_path: Path) -> None:
        """Empty file list returns default preset."""
        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=tmp_path)
        files: list[str] = []

        inferred = inference.infer_preset_from_files(files)

        # Default should be "standard" if not configured otherwise
        assert inferred in ("quick", "standard")

    def test_config_changes_escalate(self, tmp_path: Path) -> None:
        """Config file changes escalate to standard."""
        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=tmp_path)
        files = ["pyproject.toml", "setup.cfg"]

        inferred = inference.infer_preset_from_files(files)

        assert inferred == "standard"


class TestValidationPolicyResolver:
    """Test ValidationPolicyResolver as single source of truth."""

    def test_resolve_returns_policy_with_preset(self, tmp_path: Path) -> None:
        """Resolver returns ValidationPolicy with appropriate preset."""
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        # Setup minimal config
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
    standard:
      name: "Standard Validation"
      validators:
        - global-codex
        - global-claude
      evidence_required:
        - command-test.txt
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        policy = resolver.resolve(files=["README.md"])

        assert policy.preset.id == "quick"

    def test_resolve_escalates_for_code_changes(self, tmp_path: Path) -> None:
        """Resolver escalates from quick to standard for code changes."""
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  defaults:
    preset: quick
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
    standard:
      name: "Standard Validation"
      validators:
        - global-codex
        - global-claude
      evidence_required:
        - command-test.txt
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        policy = resolver.resolve(files=["src/module.py"])

        assert policy.preset.id == "standard"
        assert policy.is_escalated is True
        assert policy.escalated_from == "quick"

    def test_explicit_preset_override(self, tmp_path: Path) -> None:
        """Explicit preset parameter overrides inference."""
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
    comprehensive:
      name: "Comprehensive Validation"
      validators:
        - global-codex
        - global-claude
        - security
      evidence_required:
        - command-test.txt
        - command-lint.txt
        - command-build.txt
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        # Explicitly request comprehensive even for docs
        policy = resolver.resolve(files=["README.md"], preset_id="comprehensive")

        assert policy.preset.id == "comprehensive"
        assert policy.is_escalated is False  # Not escalated, explicitly requested

    def test_get_validators_for_task(self, tmp_path: Path) -> None:
        """Resolver provides validators list for a resolved policy."""
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        policy = resolver.resolve(files=["README.md"])

        assert policy.preset.validators == ["global-codex"]

    def test_get_evidence_requirements(self, tmp_path: Path) -> None:
        """Resolver provides evidence requirements from policy."""
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    standard:
      name: "Standard Validation"
      validators:
        - global-codex
        - global-claude
      evidence_required:
        - command-test.txt
        - command-lint.txt
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        policy = resolver.resolve(files=["src/module.py"])

        assert "command-test.txt" in policy.preset.evidence_required
        assert "command-lint.txt" in policy.preset.evidence_required


class TestEscalationRules:
    """Test escalation rules from config."""

    def test_escalation_chain_from_config(self, tmp_path: Path) -> None:
        """Escalation chain is read from config."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick"
      validators: [global-codex]
      evidence_required: []
      escalates_to: standard
    standard:
      name: "Standard"
      validators: [global-codex, global-claude]
      evidence_required: [command-test.txt]
      escalates_to: comprehensive
    comprehensive:
      name: "Comprehensive"
      validators: [global-codex, global-claude, security]
      evidence_required: [command-test.txt, command-lint.txt, command-build.txt]
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        quick = loader.get_preset("quick")

        assert quick is not None
        assert quick.escalates_to == "standard"

    def test_file_patterns_for_escalation(self, tmp_path: Path) -> None:
        """Escalation patterns are read from config."""
        from edison.core.qa.policy.config import PresetConfigLoader

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  escalation:
    # Files matching these patterns escalate above 'quick' preset
    code_patterns:
      - "*.py"
      - "*.ts"
      - "*.tsx"
      - "*.js"
    config_patterns:
      - "pyproject.toml"
      - "package.json"
      - "*.yaml"
      - "*.yml"
  presets:
    quick:
      name: "Quick"
      validators: [global-codex]
      evidence_required: []
"""
        )

        loader = PresetConfigLoader(project_root=tmp_path)
        escalation_config = loader.get_escalation_config()

        assert "*.py" in escalation_config.get("code_patterns", [])
        assert "pyproject.toml" in escalation_config.get("config_patterns", [])


class TestPolicyIntegrationWithValidatorRegistry:
    """Test policy integration with ValidatorRegistry roster building."""

    def test_roster_respects_policy_validators(self, tmp_path: Path) -> None:
        """ValidatorRegistry.build_execution_roster uses policy validators."""
        # This test verifies the integration point
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        validators_yaml = config_dir / "validators.yaml"
        validators_yaml.write_text(
            """
validation:
  presets:
    quick:
      name: "Quick Validation"
      validators:
        - global-codex
      evidence_required: []
  validators:
    global-codex:
      name: "Global Validator (Codex)"
      engine: codex-cli
      wave: critical
      always_run: true
      blocking: true
    global-claude:
      name: "Global Validator (Claude)"
      engine: claude-cli
      wave: critical
      always_run: true
      blocking: true
"""
        )

        resolver = ValidationPolicyResolver(project_root=tmp_path)
        policy = resolver.resolve(files=["README.md"])

        # Quick preset should only include global-codex
        assert policy.preset.validators == ["global-codex"]
        assert "global-claude" not in policy.preset.validators
