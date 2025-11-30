"""Tests for guidelines configuration in output config.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from tests.unit.composition.conftest import create_minimal_project, write_composition_yaml


class TestGuidelinesConfiguration:
    """Tests for guidelines configuration."""

    def test_guidelines_config_defaults(self, tmp_path: Path) -> None:
        """Guidelines config should have sensible defaults."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_guidelines_config()

        assert cfg.enabled is True
        assert cfg.preserve_structure is True

    def test_get_guidelines_dir_uses_config(self, tmp_path: Path) -> None:
        """get_guidelines_dir should use config to build path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_guidelines_dir()

        assert path is not None
        assert "_generated/guidelines" in str(path)

    def test_get_guidelines_dir_returns_none_when_disabled(self, tmp_path: Path) -> None:
        """get_guidelines_dir should return None when guidelines disabled."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  guidelines:
    enabled: false
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_guidelines_dir()

        assert path is None
