"""Tests for CompositionConfig domain class.

Tests the unified composition configuration accessor using real config files.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from edison.core.config.domains.composition import (
    CompositionConfig,
    ContentTypeConfig,
    AdapterConfig,
    AdapterSyncConfig,
)


@pytest.fixture
def minimal_config(tmp_path: Path) -> CompositionConfig:
    """Create a minimal composition config in a temporary directory."""
    # Create minimal Edison project structure
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir(parents=True)
    config_dir = edison_dir / "config"
    config_dir.mkdir()

    # Create minimal composition.yaml
    config_file = config_dir / "composition.yaml"
    config_file.write_text("""
version: "2.0"
defaults:
  composition_mode: section_merge
""")

    # Create edison.yaml project config
    project_config = tmp_path / "edison.yaml"
    project_config.write_text("project:\n  name: test-project\n")

    return CompositionConfig(repo_root=tmp_path)


class TestCompositionConfigDefaults:
    """Test default value access."""

    def test_shingle_size_default(self, minimal_config: CompositionConfig) -> None:
        """Should return default shingle_size."""
        # Default from merged composition config (bundled defaults + minimal project config)
        assert isinstance(minimal_config.shingle_size, int)
        assert minimal_config.shingle_size > 0

    def test_min_shingles_default(self, minimal_config: CompositionConfig) -> None:
        """Should return default min_shingles."""
        assert isinstance(minimal_config.min_shingles, int)
        assert minimal_config.min_shingles > 0

    def test_threshold_default(self, minimal_config: CompositionConfig) -> None:
        """Should return default threshold."""
        assert isinstance(minimal_config.threshold, float)
        assert 0 < minimal_config.threshold < 1

    def test_default_composition_mode(self, minimal_config: CompositionConfig) -> None:
        """Should return default composition mode."""
        assert minimal_config.default_composition_mode == "section_merge"


class TestCompositionConfigContentTypes:
    """Test content type access."""

    @pytest.fixture
    def config_with_content_types(self, tmp_path: Path) -> CompositionConfig:
        """Create config with test content types."""
        # Create Edison project structure
        edison_dir = tmp_path / ".edison"
        edison_dir.mkdir(parents=True)
        config_dir = edison_dir / "config"
        config_dir.mkdir()

        # Create composition.yaml with content types
        config_file = config_dir / "composition.yaml"
        config_file.write_text("""
version: "2.0"
defaults:
  composition_mode: section_merge
content_types:
  agents:
    enabled: true
    description: "Agent templates"
    content_path: "agents"
    file_pattern: "*.md"
    output_path: "{{PROJECT_EDISON_DIR}}/_generated/agents"
  validators:
    enabled: true
    description: "Validator templates"
    content_path: "validators"
  disabled_type:
    enabled: false
    description: "Disabled type"
""")

        # Create edison.yaml project config
        project_config = tmp_path / "edison.yaml"
        project_config.write_text("project:\n  name: test-project\n")

        return CompositionConfig(repo_root=tmp_path)

    def test_get_all_content_types(self, config_with_content_types: CompositionConfig) -> None:
        """Should return all content types."""
        types = config_with_content_types.content_types
        # Content types come from both bundled and project config
        assert isinstance(types, dict)

    def test_get_enabled_content_types(self, config_with_content_types: CompositionConfig) -> None:
        """Should return only enabled content types."""
        enabled = config_with_content_types.get_enabled_content_types()
        names = [t.name for t in enabled]
        # Should include agents and validators from project config
        # disabled_type should NOT be included
        assert "disabled_type" not in names

    def test_get_content_type(self, config_with_content_types: CompositionConfig) -> None:
        """Should return specific content type."""
        agents = config_with_content_types.get_content_type("agents")
        assert agents is not None
        assert agents.name == "agents"
        assert agents.enabled is True

    def test_get_nonexistent_content_type(self, config_with_content_types: CompositionConfig) -> None:
        """Should return None for nonexistent type."""
        result = config_with_content_types.get_content_type("nonexistent")
        assert result is None

    def test_content_type_cli_flag(self, config_with_content_types: CompositionConfig) -> None:
        """Should convert underscore to hyphen for cli_flag."""
        agents = config_with_content_types.get_content_type("agents")
        assert agents is not None
        assert agents.cli_flag == "agents"


class TestCompositionConfigAdapters:
    """Test adapter configuration access."""

    @pytest.fixture
    def config_with_adapters(self, tmp_path: Path) -> CompositionConfig:
        """Create config with test adapters."""
        # Create Edison project structure
        edison_dir = tmp_path / ".edison"
        edison_dir.mkdir(parents=True)
        config_dir = edison_dir / "config"
        config_dir.mkdir()

        # Create composition.yaml with adapters
        config_file = config_dir / "composition.yaml"
        config_file.write_text("""
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
""")

        # Create edison.yaml project config
        project_config = tmp_path / "edison.yaml"
        project_config.write_text("project:\n  name: test-project\n")

        return CompositionConfig(repo_root=tmp_path)

    def test_get_all_adapters(self, config_with_adapters: CompositionConfig) -> None:
        """Should return all adapters."""
        adapters = config_with_adapters.adapters
        # Should include adapters from project config
        assert isinstance(adapters, dict)

    def test_get_enabled_adapters(self, config_with_adapters: CompositionConfig) -> None:
        """Should return only enabled adapters."""
        enabled = config_with_adapters.get_enabled_adapters()
        names = [a.name for a in enabled]
        # disabled_adapter should NOT be included
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

    def test_resolve_output_path_empty(self, minimal_config: CompositionConfig) -> None:
        """Should return repo_root for empty path."""
        result = minimal_config.resolve_output_path("")
        assert result == minimal_config.repo_root

    def test_resolve_output_path_relative(self, minimal_config: CompositionConfig) -> None:
        """Should resolve relative paths from repo_root."""
        result = minimal_config.resolve_output_path(".cursor")
        assert result == minimal_config.repo_root / ".cursor"

    def test_resolve_output_path_with_placeholder(self, minimal_config: CompositionConfig) -> None:
        """Should resolve {{PROJECT_EDISON_DIR}} placeholder."""
        result = minimal_config.resolve_output_path("{{PROJECT_EDISON_DIR}}/_generated")
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
