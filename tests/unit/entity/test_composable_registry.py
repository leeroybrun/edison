"""Tests for ComposableRegistry base class.

TDD: These tests are written FIRST before implementation.

ComposableRegistry is the unified base class for ALL file-based registries:
- Uses LayerDiscovery for file discovery
- Uses MarkdownCompositionStrategy for composition
- Subclasses define: content_type, file_pattern, strategy_config
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest


# Note: TestEntity removed to avoid pytest collection warning


class TestComposableRegistryBase:
    """Base tests for ComposableRegistry."""

    def test_registry_is_abstract(self) -> None:
        """ComposableRegistry cannot be instantiated directly."""
        from edison.core.entity.composable_registry import ComposableRegistry

        # ComposableRegistry requires content_type to be defined
        with pytest.raises(NotImplementedError):
            ComposableRegistry()  # type: ignore[abstract]

    def test_subclass_requires_content_type(self, isolated_project_env: Path) -> None:
        """Subclass must define content_type."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class IncompleteRegistry(ComposableRegistry[str]):
            # Missing content_type
            file_pattern = "*.md"

        with pytest.raises(NotImplementedError):
            IncompleteRegistry()

    def test_subclass_with_all_required_attributes(
        self, isolated_project_env: Path
    ) -> None:
        """Subclass with all required attributes can be instantiated."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test-content"
            file_pattern = "*.md"
            strategy_config = {"enable_sections": True}

        registry = TestRegistry()

        assert registry.content_type == "test-content"
        assert registry.file_pattern == "*.md"
        assert registry.strategy_config["enable_sections"] is True


class TestComposableRegistryDiscovery:
    """Tests for file discovery via LayerDiscovery."""

    def test_discover_core_uses_layer_discovery(
        self, isolated_project_env: Path
    ) -> None:
        """discover_core delegates to LayerDiscovery."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class TestRegistry(ComposableRegistry[str]):
            content_type = "agents"
            file_pattern = "*.md"
            strategy_config = {}

        registry = TestRegistry()

        # Should discover from bundled core data
        core_entities = registry.discover_core()

        # Should return dict of name -> path (or similar)
        assert isinstance(core_entities, dict)

    def test_discover_project_finds_project_files(
        self, isolated_project_env: Path
    ) -> None:
        """discover_project finds files in .edison/{content_type}/."""
        from edison.core.entity.composable_registry import ComposableRegistry

        root = isolated_project_env

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test-items"
            file_pattern = "*.md"
            strategy_config = {}

        # Create project-level content
        project_dir = root / ".edison" / "test-items"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "my-item.md").write_text("# My Item\n\nContent.\n")

        registry = TestRegistry()
        project_entities = registry.discover_project()

        assert "my-item" in project_entities

    def test_discover_packs_finds_pack_files(
        self, isolated_project_env: Path
    ) -> None:
        """discover_packs finds files in .edison/packs/{pack}/{content_type}/."""
        from edison.core.entity.composable_registry import ComposableRegistry

        root = isolated_project_env

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test-items"
            file_pattern = "*.md"
            strategy_config = {}

        # Create pack-level content
        pack_dir = root / ".edison" / "packs" / "my-pack" / "test-items"
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "pack-item.md").write_text("# Pack Item\n\nPack content.\n")

        registry = TestRegistry()
        pack_entities = registry.discover_packs(["my-pack"])

        assert "pack-item" in pack_entities


class TestComposableRegistryComposition:
    """Tests for composition via MarkdownCompositionStrategy."""

    def test_compose_uses_strategy(self, isolated_project_env: Path) -> None:
        """compose() delegates to MarkdownCompositionStrategy."""
        from edison.core.entity.composable_registry import ComposableRegistry

        root = isolated_project_env

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test-items"
            file_pattern = "*.md"
            strategy_config = {"enable_sections": True, "enable_dedupe": False}

        # Create project-level content with sections
        project_dir = root / ".edison" / "test-items"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "my-item.md").write_text(
            """# My Item
<!-- SECTION: intro -->
Introduction content.
<!-- /SECTION: intro -->
"""
        )

        registry = TestRegistry()
        result = registry.compose("my-item", packs=[])

        # Should return composed content
        assert result is not None
        assert "Introduction content." in str(result)

    def test_compose_with_project_overlays(self, isolated_project_env: Path) -> None:
        """compose() applies project overlays via EXTEND markers."""
        from edison.core.entity.composable_registry import ComposableRegistry

        root = isolated_project_env

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test-items"
            file_pattern = "*.md"
            strategy_config = {"enable_sections": True}

        # Create pack entity (base content) - pack-new entity
        pack_dir = root / ".edison" / "packs" / "my-pack" / "test-items"
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "my-item.md").write_text(
            """# My Item
<!-- SECTION: intro -->
Base intro.
<!-- /SECTION: intro -->
"""
        )

        # Create project overlay (extends the pack entity)
        overlay_dir = root / ".edison" / "test-items" / "overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        (overlay_dir / "my-item.md").write_text(
            """<!-- EXTEND: intro -->
Project extension.
<!-- /EXTEND -->
"""
        )

        registry = TestRegistry()
        result = registry.compose("my-item", packs=["my-pack"])

        # Should include both base and extension
        result_str = str(result)
        assert "Base intro." in result_str
        assert "Project extension." in result_str

    def test_compose_with_dedupe_enabled(self, isolated_project_env: Path) -> None:
        """compose() deduplicates when strategy_config enables it."""
        from edison.core.entity.composable_registry import ComposableRegistry

        root = isolated_project_env

        class DedupeRegistry(ComposableRegistry[str]):
            content_type = "test-items"
            file_pattern = "*.md"
            strategy_config = {
                "enable_sections": False,
                "enable_dedupe": True,
                "dedupe_shingle_size": 6,
            }

        # Create content with duplicates
        duplicate_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

        project_dir = root / ".edison" / "test-items"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "my-item.md").write_text(f"# My Item\n\n{duplicate_text}\n")

        pack_dir = root / ".edison" / "packs" / "my-pack" / "test-items"
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "my-item.md").write_text(f"# Pack\n\n{duplicate_text}\n")

        registry = DedupeRegistry()
        result = registry.compose("my-item", packs=["my-pack"])

        # Duplicate should appear only once
        result_str = str(result)
        assert result_str.count(duplicate_text) == 1


class TestComposableRegistryStrategyConfig:
    """Tests for strategy configuration."""

    def test_default_strategy_config(self, isolated_project_env: Path) -> None:
        """Default strategy_config has sensible defaults."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class DefaultRegistry(ComposableRegistry[str]):
            content_type = "test"
            file_pattern = "*.md"
            # No strategy_config override - uses default

        registry = DefaultRegistry()

        # Should have default config
        config = registry.get_strategy_config()
        assert "enable_sections" in config
        assert "enable_dedupe" in config

    def test_custom_strategy_config_override(
        self, isolated_project_env: Path
    ) -> None:
        """Custom strategy_config overrides defaults."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class CustomRegistry(ComposableRegistry[str]):
            content_type = "test"
            file_pattern = "*.md"
            strategy_config = {
                "enable_sections": False,
                "enable_dedupe": True,
                "dedupe_shingle_size": 8,
            }

        registry = CustomRegistry()
        config = registry.get_strategy_config()

        assert config["enable_sections"] is False
        assert config["enable_dedupe"] is True
        assert config["dedupe_shingle_size"] == 8


class TestComposableRegistryInheritance:
    """Tests for inheritance from CompositionBase."""

    def test_inherits_path_resolution(self, isolated_project_env: Path) -> None:
        """ComposableRegistry has path resolution from CompositionBase."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test"
            file_pattern = "*.md"
            strategy_config = {}

        registry = TestRegistry()

        # Should have path attributes from CompositionBase
        assert hasattr(registry, "project_root")
        assert hasattr(registry, "project_dir")
        assert hasattr(registry, "core_dir")
        assert hasattr(registry, "bundled_packs_dir")
        assert hasattr(registry, "project_packs_dir")

    def test_inherits_config_management(self, isolated_project_env: Path) -> None:
        """ComposableRegistry has config management from CompositionBase."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test"
            file_pattern = "*.md"
            strategy_config = {}

        registry = TestRegistry()

        # Should have config from CompositionBase
        assert hasattr(registry, "cfg_mgr")
        assert hasattr(registry, "config")
        assert isinstance(registry.config, dict)

    def test_inherits_active_packs(self, isolated_project_env: Path) -> None:
        """ComposableRegistry has get_active_packs from CompositionBase."""
        from edison.core.entity.composable_registry import ComposableRegistry

        class TestRegistry(ComposableRegistry[str]):
            content_type = "test"
            file_pattern = "*.md"
            strategy_config = {}

        registry = TestRegistry()

        # Should have get_active_packs method
        packs = registry.get_active_packs()
        assert isinstance(packs, list)
