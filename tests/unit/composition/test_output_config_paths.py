"""Tests for path resolution in output configuration.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from .conftest import create_minimal_project, write_composition_yaml


class TestPathResolution:
    """Tests for path resolution with placeholders and relative paths."""

    def test_resolve_path_with_placeholder(self, tmp_path: Path) -> None:
        """Path resolver should replace {{PROJECT_EDISON_DIR}} placeholder."""
        project_config_dir = tmp_path / ".custom-edison"
        project_config_dir.mkdir()

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        resolved = loader._resolve_path("{{PROJECT_EDISON_DIR}}/_generated/agents")

        assert resolved == project_config_dir / "_generated" / "agents"

    def test_resolve_path_relative_to_repo_root(self, tmp_path: Path) -> None:
        """Relative paths should resolve relative to repo root."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        resolved = loader._resolve_path(".claude/agents")

        assert resolved == tmp_path / ".claude" / "agents"

    def test_resolve_path_absolute_unchanged(self, tmp_path: Path) -> None:
        """Absolute paths should remain unchanged."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        resolved = loader._resolve_path("/absolute/path/to/agents")

        assert resolved == Path("/absolute/path/to/agents")

    def test_get_agent_path_uses_config(self, tmp_path: Path) -> None:
        """get_agent_path should use config to build full path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_agent_path("feature-implementer")

        assert path is not None
        assert path.name == "feature-implementer.md"
        assert "_generated/agents" in str(path) or "_generated" in str(path)

    def test_get_agent_path_with_custom_pattern(self, tmp_path: Path) -> None:
        """get_agent_path should use custom filename pattern from config."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  agents:
    filename_pattern: "{name}-prompt.md"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_agent_path("feature-implementer")

        assert path is not None
        assert path.name == "feature-implementer-prompt.md"

    def test_get_validator_path_uses_config(self, tmp_path: Path) -> None:
        """get_validator_path should use config to build full path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_validator_path("security")

        assert path is not None
        assert path.name == "security.md"

    def test_get_canonical_entry_path_uses_config(self, tmp_path: Path) -> None:
        """get_canonical_entry_path should use config to build full path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_canonical_entry_path()

        assert path is not None
        assert path == tmp_path / "AGENTS.md"

    def test_get_canonical_entry_path_with_custom_config(self, tmp_path: Path) -> None:
        """get_canonical_entry_path should respect custom config."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    output_path: "docs"
    filename: "AI_AGENTS.md"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_canonical_entry_path()

        assert path is not None
        assert path == tmp_path / "docs" / "AI_AGENTS.md"

    def test_get_canonical_entry_path_returns_none_when_disabled(self, tmp_path: Path) -> None:
        """get_canonical_entry_path should return None when disabled."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    enabled: false
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_canonical_entry_path()

        assert path is None

    def test_get_client_path_uses_config(self, tmp_path: Path) -> None:
        """get_client_path should use config to build full path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_client_path("claude")

        assert path is not None
        assert path == tmp_path / ".claude" / "CLAUDE.md"

    def test_get_client_path_returns_none_when_disabled(self, tmp_path: Path) -> None:
        """get_client_path should return None for disabled clients."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_client_path("codex")  # Disabled by default

        assert path is None
