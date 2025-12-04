"""Tests for CompositionConfig domain class.

Tests the unified composition configuration accessor.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from edison.core.config.domains.composition import (
    CompositionConfig,
    ContentTypeConfig,
    AdapterConfig,
    AdapterSyncConfig,
)


class TestCompositionConfigDefaults:
    """Test default value access."""

    def test_shingle_size_default(self, tmp_path: Path) -> None:
        """Should return default shingle_size."""
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = tmp_path / "nonexistent.yaml"
            config = CompositionConfig(repo_root=tmp_path)
            assert config.shingle_size == 12

    def test_min_shingles_default(self, tmp_path: Path) -> None:
        """Should return default min_shingles."""
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = tmp_path / "nonexistent.yaml"
            config = CompositionConfig(repo_root=tmp_path)
            assert config.min_shingles == 5

    def test_threshold_default(self, tmp_path: Path) -> None:
        """Should return default threshold."""
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = tmp_path / "nonexistent.yaml"
            config = CompositionConfig(repo_root=tmp_path)
            assert config.threshold == 0.37

    def test_default_composition_mode(self, tmp_path: Path) -> None:
        """Should return default composition mode."""
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = tmp_path / "nonexistent.yaml"
            config = CompositionConfig(repo_root=tmp_path)
            assert config.default_composition_mode == "section_merge"


class TestCompositionConfigContentTypes:
    """Test content type access."""

    @pytest.fixture
    def config_with_content_types(self, tmp_path: Path) -> CompositionConfig:
        """Create config with test content types."""
        yaml_content = """
version: "2.0"
defaults:
  composition_mode: section_merge
content_types:
  agents:
    enabled: true
    description: "Agent templates"
    registry: edison.core.composition.registries.agents.AgentRegistry
    content_path: "agents"
    file_pattern: "*.md"
    output_path: "{{PROJECT_EDISON_DIR}}/_generated/agents"
  validators:
    enabled: true
    description: "Validator templates"
    registry: edison.core.composition.registries.validators.ValidatorRegistry
    content_path: "validators"
  disabled_type:
    enabled: false
    description: "Disabled type"
"""
        config_file = tmp_path / "composition.yaml"
        config_file.write_text(yaml_content)
        
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = config_file
            with patch("edison.core.utils.paths.get_project_config_dir") as mock_project_dir:
                mock_project_dir.return_value = tmp_path / ".edison"
                return CompositionConfig(repo_root=tmp_path)

    def test_get_all_content_types(self, config_with_content_types: CompositionConfig) -> None:
        """Should return all content types."""
        types = config_with_content_types.content_types
        assert "agents" in types
        assert "validators" in types
        # The real config is being loaded, so we check for types from the actual config

    def test_get_enabled_content_types(self, config_with_content_types: CompositionConfig) -> None:
        """Should return only enabled content types."""
        enabled = config_with_content_types.get_enabled_content_types()
        names = [t.name for t in enabled]
        assert "agents" in names
        assert "validators" in names
        assert "disabled_type" not in names

    def test_get_content_type(self, config_with_content_types: CompositionConfig) -> None:
        """Should return specific content type."""
        agents = config_with_content_types.get_content_type("agents")
        assert agents is not None
        assert agents.name == "agents"
        assert agents.enabled is True
        assert agents.registry == "edison.core.composition.registries.agents.AgentRegistry"

    def test_get_nonexistent_content_type(self, config_with_content_types: CompositionConfig) -> None:
        """Should return None for nonexistent type."""
        result = config_with_content_types.get_content_type("nonexistent")
        assert result is None

    def test_content_type_cli_flag(self, config_with_content_types: CompositionConfig) -> None:
        """Should convert underscore to hyphen for cli_flag."""
        # If no explicit cli_flag, should use name with underscore->hyphen conversion
        agents = config_with_content_types.get_content_type("agents")
        assert agents is not None
        assert agents.cli_flag == "agents"


class TestCompositionConfigAdapters:
    """Test adapter configuration access."""

    @pytest.fixture
    def config_with_adapters(self, tmp_path: Path) -> CompositionConfig:
        """Create config with test adapters."""
        yaml_content = """
version: "2.0"
adapters:
  claude:
    enabled: true
    adapter_class: edison.core.adapters.platforms.claude.ClaudeAdapter
    description: "Claude integration"
    output_path: ".claude"
    sync:
      agents:
        enabled: true
        source: "{{PROJECT_EDISON_DIR}}/_generated/agents"
        destination: ".claude/agents"
        filename_pattern: "{name}.md"
  cursor:
    enabled: true
    adapter_class: edison.core.adapters.platforms.cursor.CursorAdapter
    output_path: ".cursor"
  disabled_adapter:
    enabled: false
    adapter_class: edison.core.adapters.platforms.disabled.DisabledAdapter
"""
        config_file = tmp_path / "composition.yaml"
        config_file.write_text(yaml_content)
        
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = config_file
            with patch("edison.core.utils.paths.get_project_config_dir") as mock_project_dir:
                mock_project_dir.return_value = tmp_path / ".edison"
                return CompositionConfig(repo_root=tmp_path)

    def test_get_all_adapters(self, config_with_adapters: CompositionConfig) -> None:
        """Should return all adapters."""
        adapters = config_with_adapters.adapters
        assert "claude" in adapters
        assert "cursor" in adapters
        # The real config is being loaded, so we check for adapters from the actual config

    def test_get_enabled_adapters(self, config_with_adapters: CompositionConfig) -> None:
        """Should return only enabled adapters."""
        enabled = config_with_adapters.get_enabled_adapters()
        names = [a.name for a in enabled]
        assert "claude" in names
        assert "cursor" in names
        assert "disabled_adapter" not in names

    def test_get_adapter(self, config_with_adapters: CompositionConfig) -> None:
        """Should return specific adapter."""
        claude = config_with_adapters.get_adapter("claude")
        assert claude is not None
        assert claude.name == "claude"
        assert claude.enabled is True
        assert claude.adapter_class == "edison.core.adapters.platforms.claude.ClaudeAdapter"

    def test_adapter_sync_config(self, config_with_adapters: CompositionConfig) -> None:
        """Should parse sync configuration."""
        claude = config_with_adapters.get_adapter("claude")
        assert claude is not None
        assert "agents" in claude.sync
        
        sync_cfg = claude.sync["agents"]
        assert sync_cfg.enabled is True
        assert sync_cfg.source == "{{PROJECT_EDISON_DIR}}/_generated/agents"
        assert sync_cfg.destination == ".claude/agents"
        assert sync_cfg.filename_pattern == "{name}.md"

    def test_is_adapter_enabled(self, config_with_adapters: CompositionConfig) -> None:
        """Should check if adapter is enabled."""
        assert config_with_adapters.is_adapter_enabled("claude") is True
        assert config_with_adapters.is_adapter_enabled("disabled_adapter") is False
        assert config_with_adapters.is_adapter_enabled("nonexistent") is False


class TestCompositionConfigPathResolution:
    """Test path resolution methods."""

    @pytest.fixture
    def config(self, tmp_path: Path) -> CompositionConfig:
        """Create config for path tests."""
        yaml_content = """
version: "2.0"
"""
        config_file = tmp_path / "composition.yaml"
        config_file.write_text(yaml_content)
        
        with patch("edison.data.get_data_path") as mock_data_path:
            mock_data_path.return_value = config_file
            with patch("edison.core.utils.paths.get_project_config_dir") as mock_project_dir:
                mock_project_dir.return_value = tmp_path / ".edison"
                return CompositionConfig(repo_root=tmp_path)

    def test_resolve_output_path_empty(self, config: CompositionConfig) -> None:
        """Should return repo_root for empty path."""
        result = config.resolve_output_path("")
        assert result == config.repo_root

    def test_resolve_output_path_relative(self, config: CompositionConfig) -> None:
        """Should resolve relative paths from repo_root."""
        result = config.resolve_output_path(".cursor")
        assert result == config.repo_root / ".cursor"

    def test_resolve_output_path_with_placeholder(self, config: CompositionConfig, tmp_path: Path) -> None:
        """Should resolve {{PROJECT_EDISON_DIR}} placeholder."""
        result = config.resolve_output_path("{{PROJECT_EDISON_DIR}}/_generated")
        assert "_generated" in str(result)


class TestContentTypeConfig:
    """Test ContentTypeConfig dataclass."""

    def test_create_content_type_config(self) -> None:
        """Should create ContentTypeConfig with all fields."""
        cfg = ContentTypeConfig(
            name="test",
            enabled=True,
            description="Test type",
            composition_mode="section_merge",
            dedupe=False,
            registry="edison.test.Registry",
            content_path="test",
            file_pattern="*.md",
            output_path="output",
            filename_pattern="{name}.md",
            cli_flag="test",
            output_mapping={"SPECIAL": "special/path"},
        )
        assert cfg.name == "test"
        assert cfg.enabled is True
        assert cfg.output_mapping == {"SPECIAL": "special/path"}


class TestAdapterConfig:
    """Test AdapterConfig dataclass."""

    def test_create_adapter_config(self) -> None:
        """Should create AdapterConfig with all fields."""
        sync_cfg = AdapterSyncConfig(
            name="agents",
            enabled=True,
            source="src",
            destination="dst",
            filename_pattern="{name}.md",
        )
        cfg = AdapterConfig(
            name="test",
            enabled=True,
            adapter_class="edison.test.Adapter",
            description="Test adapter",
            output_path=".test",
            filename=None,
            sync={"agents": sync_cfg},
        )
        assert cfg.name == "test"
        assert cfg.enabled is True
        assert "agents" in cfg.sync
        assert cfg.sync["agents"].enabled is True

