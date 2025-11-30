"""Tests for sync configuration in output config.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from tests.unit.composition.conftest import create_minimal_project, write_composition_yaml


class TestSyncConfiguration:
    """Tests for sync configuration (Claude, Zen, etc.)."""

    def test_sync_config_claude_defaults(self, tmp_path: Path) -> None:
        """Claude sync config should have sensible defaults."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_sync_config("claude")

        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.agents_path == ".claude/agents"
        assert cfg.agents_filename_pattern == "{name}.md"

    def test_sync_config_zen_defaults(self, tmp_path: Path) -> None:
        """Zen sync config should have sensible defaults."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_sync_config("zen")

        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.prompts_path == ".zen/conf/systemprompts/clink"

    def test_get_sync_agents_dir_uses_config(self, tmp_path: Path) -> None:
        """get_sync_agents_dir should use config to build path."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_sync_agents_dir("claude")

        assert path is not None
        assert path == tmp_path / ".claude" / "agents"

    def test_get_sync_agents_dir_with_custom_config(self, tmp_path: Path) -> None:
        """get_sync_agents_dir should respect custom config."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  sync:
    claude:
      agents_path: ".ai/claude-agents"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        path = loader.get_sync_agents_dir("claude")

        assert path is not None
        assert path == tmp_path / ".ai" / "claude-agents"
