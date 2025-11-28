"""Tests for project configuration overrides.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from .conftest import create_minimal_project, write_composition_yaml


class TestProjectOverrides:
    """Tests for project config overriding core defaults."""

    def test_project_config_override_disables_client(self, tmp_path: Path) -> None:
        """Project config should override core defaults - disable client."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  clients:
    claude:
      enabled: false
      filename: "MY_CLAUDE.md"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_client_config("claude")

        assert cfg is not None
        assert cfg.enabled is False
        assert cfg.filename == "MY_CLAUDE.md"

    def test_project_config_override_changes_canonical_entry(self, tmp_path: Path) -> None:
        """Project config should allow changing canonical entry filename and path."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    filename: "AGENTS_COMPOSED.md"
    output_path: "docs"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_canonical_entry_config()

        assert cfg.filename == "AGENTS_COMPOSED.md"
        assert cfg.output_path == "docs"

    def test_project_config_override_enables_disabled_client(self, tmp_path: Path) -> None:
        """Project config should allow enabling a disabled client."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  clients:
    codex:
      enabled: true
      output_path: "~/.codex/prompts"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_client_config("codex")

        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.output_path == "~/.codex/prompts"

    def test_project_config_override_custom_agent_pattern(self, tmp_path: Path) -> None:
        """Project config should allow custom filename patterns for agents."""
        project_config_dir = create_minimal_project(tmp_path)

        write_composition_yaml(project_config_dir, """
outputs:
  agents:
    output_path: ".ai/agents"
    filename_pattern: "{name}-agent.md"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_agents_config()

        assert cfg.output_path == ".ai/agents"
        assert cfg.filename_pattern == "{name}-agent.md"

    def test_deep_merge_preserves_unset_values(self, tmp_path: Path) -> None:
        """Deep merge should preserve core values not overridden by project."""
        project_config_dir = create_minimal_project(tmp_path)

        # Only override one client, others should remain from core
        write_composition_yaml(project_config_dir, """
outputs:
  clients:
    claude:
      filename: "CUSTOM_CLAUDE.md"
""")

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        # Claude filename changed
        claude_cfg = loader.get_client_config("claude")
        assert claude_cfg.filename == "CUSTOM_CLAUDE.md"
        # But claude is still enabled (from core defaults)
        assert claude_cfg.enabled is True

        # Zen unchanged (not in project config)
        zen_cfg = loader.get_client_config("zen")
        assert zen_cfg.enabled is True
        assert zen_cfg.filename == "zen.md"
