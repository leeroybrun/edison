"""Tests for validation preset configuration loading.

RED phase: These tests verify that presets are correctly loaded from YAML config
with proper merging of core -> packs -> project layers.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import (
    create_repo_with_git,
    create_edison_config_structure,
    setup_project_root,
)
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


@pytest.mark.qa
class TestPresetConfigLoading:
    """Tests for loading preset configuration from YAML."""

    def test_required_evidence_semantics_are_tristate(self, tmp_path: Path, monkeypatch):
        """Presets must support tri-state required_evidence semantics (None vs [] vs explicit list).

        This is behavior, not a config contract: tests must not pin specific bundled presets/validators.
        """
        repo = create_repo_with_git(tmp_path)
        create_edison_config_structure(repo)

        cfg_dir = repo / ".edison" / "config"
        write_yaml(
            cfg_dir / "validation.yaml",
            {
                "validation": {
                    "presets": {
                        "inherit": {"name": "inherit", "validators": []},
                        "none": {"name": "none", "validators": [], "required_evidence": []},
                        "explicit": {
                            "name": "explicit",
                            "validators": [],
                            "required_evidence": ["command-test-full.txt"],
                        },
                    }
                }
            },
        )

        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        presets = loader.load_presets()

        assert presets["inherit"].required_evidence is None
        assert presets["none"].required_evidence == []
        assert presets["explicit"].required_evidence == ["command-test-full.txt"]

    def test_project_can_override_preset(self, tmp_path: Path, monkeypatch):
        """Project-level config can override preset validators."""
        repo = create_repo_with_git(tmp_path)

        # Create project-level preset override
        config_dir = repo / ".edison" / "config"
        write_yaml(
            config_dir / "validation.yaml",
            {
                "validation": {
                    "presets": {
                        "quick": {
                            "name": "quick",
                            "validators": ["custom-validator"],
                            "required_evidence": ["custom-report.md"],
                        }
                    }
                }
            },
        )

        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        presets = loader.load_presets()

        quick = presets["quick"]
        assert "custom-validator" in quick.validators
        assert "custom-report.md" in quick.required_evidence

    def test_project_can_add_new_preset(self, tmp_path: Path, monkeypatch):
        """Project-level config can define completely new presets."""
        repo = create_repo_with_git(tmp_path)

        # Create project-specific preset
        config_dir = repo / ".edison" / "config"
        write_yaml(
            config_dir / "validation.yaml",
            {
                "validation": {
                    "presets": {
                        "typescript-strict": {
                            "name": "typescript-strict",
                            "validators": ["typescript"],
                            "required_evidence": ["command-type-check.txt", "command-lint.txt"],
                            "blocking_validators": ["typescript"],
                        }
                    }
                }
            },
        )

        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        presets = loader.load_presets()

        assert "typescript-strict" in presets
        ts_preset = presets["typescript-strict"]
        assert ts_preset.validators == ["typescript"]
        assert "typescript" in ts_preset.blocking_validators

    def test_get_preset_by_name(self, tmp_path: Path, monkeypatch):
        """PresetConfigLoader.get_preset returns a specific preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        quick = loader.get_preset("quick")

        assert quick is not None
        assert quick.name == "quick"

    def test_get_preset_returns_none_for_unknown(self, tmp_path: Path, monkeypatch):
        """PresetConfigLoader.get_preset returns None for unknown preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        result = loader.get_preset("nonexistent-preset")

        assert result is None


@pytest.mark.qa
class TestPresetInferenceRules:
    """Tests for loading file pattern to preset inference rules."""

    def test_project_can_add_inference_rules(self, tmp_path: Path, monkeypatch):
        """Project can add custom file pattern inference rules."""
        repo = create_repo_with_git(tmp_path)

        config_dir = repo / ".edison" / "config"
        write_yaml(
            config_dir / "validation.yaml",
            {
                "validation": {
                    "presetInference": {
                        "rules": [
                            {
                                "patterns": ["*.prisma"],
                                "preset": "database",
                                "priority": 100,
                            }
                        ]
                    }
                }
            },
        )

        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.config import PresetConfigLoader

        loader = PresetConfigLoader(project_root=repo)
        rules = loader.load_inference_rules()

        prisma_rule = next((r for r in rules if "*.prisma" in r.get("patterns", [])), None)
        assert prisma_rule is not None
        assert prisma_rule["preset"] == "database"
