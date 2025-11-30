"""Tests for output configuration defaults.

All tests use isolated tmp folders - NO MOCKS.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import OutputConfigLoader
from tests.unit.composition.conftest import create_minimal_project


class TestDefaultConfiguration:
    """Tests for default configuration loading from core data."""

    def test_output_config_loader_loads_defaults(self, tmp_path: Path) -> None:
        """OutputConfigLoader should load default configuration from core data."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)

        outputs = loader.get_outputs_config()

        assert "canonical_entry" in outputs
        assert "clients" in outputs
        assert "constitutions" in outputs
        assert "agents" in outputs
        assert "validators" in outputs

    def test_canonical_entry_config_defaults(self, tmp_path: Path) -> None:
        """Canonical entry should have sensible defaults from core config."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_canonical_entry_config()

        assert cfg.enabled is True
        assert cfg.output_path == "."
        assert cfg.filename == "AGENTS.md"

    def test_client_config_claude_defaults(self, tmp_path: Path) -> None:
        """Claude client should be enabled by default."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_client_config("claude")

        assert cfg is not None
        assert cfg.enabled is True
        assert cfg.filename == "CLAUDE.md"
        assert cfg.output_path == ".claude"

    def test_client_config_codex_disabled_by_default(self, tmp_path: Path) -> None:
        """Codex client should be disabled by default."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_client_config("codex")

        assert cfg is not None
        assert cfg.enabled is False

    def test_agents_config_defaults(self, tmp_path: Path) -> None:
        """Agents config should have sensible defaults."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_agents_config()

        assert cfg.enabled is True
        assert "{{PROJECT_EDISON_DIR}}" in cfg.output_path
        assert cfg.filename_pattern == "{name}.md"

    def test_validators_config_defaults(self, tmp_path: Path) -> None:
        """Validators config should have sensible defaults."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        cfg = loader.get_validators_config()

        assert cfg.enabled is True
        assert "{{PROJECT_EDISON_DIR}}" in cfg.output_path
        assert cfg.filename_pattern == "{name}.md"

    def test_get_enabled_clients_returns_only_enabled(self, tmp_path: Path) -> None:
        """get_enabled_clients should only return enabled clients."""
        project_config_dir = create_minimal_project(tmp_path)

        loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
        enabled = loader.get_enabled_clients()

        # Claude and Zen are enabled by default
        assert "claude" in enabled
        assert "zen" in enabled
        # Codex and Cursor are disabled by default
        assert "codex" not in enabled
        assert "cursor" not in enabled
