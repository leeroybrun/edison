"""Tests for constitution configuration in output config.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from tests.unit.composition.conftest import create_minimal_project, write_composition_yaml


class TestConstitutionConfiguration:
    """Tests for constitution file configuration."""

    def test_constitution_path_orchestrators(self, tmp_path: Path) -> None:
        """get_constitution_path should return correct path for orchestrators."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_constitution_path("orchestrators")

        assert path is not None
        assert path.name == "ORCHESTRATORS.md"

    def test_constitution_path_agents(self, tmp_path: Path) -> None:
        """get_constitution_path should return correct path for agents."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_constitution_path("agents")

        assert path is not None
        assert path.name == "AGENTS.md"

    def test_constitution_path_validators(self, tmp_path: Path) -> None:
        """get_constitution_path should return correct path for validators."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_constitution_path("validators")

        assert path is not None
        assert path.name == "VALIDATORS.md"

    def test_constitution_path_returns_none_when_disabled(self, tmp_path: Path) -> None:
        """get_constitution_path should return None when constitutions disabled."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  constitutions:
    enabled: false
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_constitution_path("orchestrators")

        assert path is None

    def test_constitution_path_individual_role_disabled(self, tmp_path: Path) -> None:
        """get_constitution_path should return None when specific role disabled."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  constitutions:
    files:
      validators:
        enabled: false
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        # Validators disabled
        val_path = loader.get_constitution_path("validators")
        assert val_path is None

        # Others still enabled
        orch_path = loader.get_constitution_path("orchestrators")
        assert orch_path is not None
