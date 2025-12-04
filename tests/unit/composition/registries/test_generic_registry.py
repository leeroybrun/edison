"""Tests for GenericRegistry (TDD - tests written FIRST).

GenericRegistry is a config-driven registry for simple content types that
don't need custom post-processing logic. It allows creating registries
dynamically via constructor parameters instead of class attributes.

Usage:
    roots = GenericRegistry("roots", project_root=project_root)
    content = roots.compose("AGENTS", packs)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest


class TestGenericRegistryConstruction:
    """Tests for GenericRegistry construction."""

    def test_creates_registry_with_content_type(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry accepts content_type as constructor param."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry("roots", project_root=isolated_project_env)

        assert registry.content_type == "roots"

    def test_creates_registry_with_custom_file_pattern(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry accepts custom file_pattern."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry(
            "custom-type",
            project_root=isolated_project_env,
            file_pattern="*.txt",
        )

        assert registry.file_pattern == "*.txt"

    def test_default_file_pattern_is_markdown(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry defaults to *.md file pattern."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry("test", project_root=isolated_project_env)

        assert registry.file_pattern == "*.md"


class TestGenericRegistryDiscovery:
    """Tests for file discovery with GenericRegistry."""

    def test_discovers_project_files(self, isolated_project_env: Path) -> None:
        """GenericRegistry discovers files from .edison/{content_type}/."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid conflict with bundled content
        content_dir = isolated_project_env / ".edison" / "test-project-content"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "ENTRY.md").write_text("# Entry Point\n\nRead ENTRY.md.\n")

        registry = GenericRegistry("test-project-content", project_root=isolated_project_env)
        entities = registry.discover_project()

        assert "ENTRY" in entities

    def test_discovers_pack_files(self, isolated_project_env: Path) -> None:
        """GenericRegistry discovers files from packs."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Create pack-level content with unique content_type
        pack_dir = isolated_project_env / ".edison" / "packs" / "test-pack" / "test-pack-content"
        pack_dir.mkdir(parents=True, exist_ok=True)
        (pack_dir / "ENTRY.md").write_text("# Pack Entry\n\nPack content.\n")

        registry = GenericRegistry("test-pack-content", project_root=isolated_project_env)
        entities = registry.discover_packs(["test-pack"])

        assert "ENTRY" in entities

    def test_list_names_returns_sorted_names(
        self, isolated_project_env: Path
    ) -> None:
        """list_names() returns sorted list of entity names."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid core bundled files
        content_dir = isolated_project_env / ".edison" / "test-unique-docs"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "zebra.md").write_text("# Zebra\n")
        (content_dir / "alpha.md").write_text("# Alpha\n")
        (content_dir / "beta.md").write_text("# Beta\n")

        registry = GenericRegistry("test-unique-docs", project_root=isolated_project_env)
        names = registry.list_names()

        assert names == ["alpha", "beta", "zebra"]


class TestGenericRegistryComposition:
    """Tests for composition with GenericRegistry."""

    def test_compose_returns_content(self, isolated_project_env: Path) -> None:
        """compose() returns composed markdown content."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid conflict with bundled content
        content_dir = isolated_project_env / ".edison" / "test-compose-content"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "ENTRY.md").write_text("# ENTRY\n\nEntry point content.\n")

        registry = GenericRegistry("test-compose-content", project_root=isolated_project_env)
        content = registry.compose("ENTRY", packs=[])

        assert content is not None
        assert "Entry point content." in str(content)

    def test_compose_with_sections(self, isolated_project_env: Path) -> None:
        """compose() handles SECTION markers when enabled via config."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid conflict with bundled content
        content_dir = isolated_project_env / ".edison" / "test-section-content"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "ENTRY.md").write_text(
            """# ENTRY
<!-- SECTION: intro -->
Introduction section.
<!-- /SECTION: intro -->
"""
        )

        # Create composition.yaml with sections enabled
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "composition.yaml").write_text(
            """
composition:
  content_types:
    test-section-content:
      known_sections:
        - intro
        - body
"""
        )

        registry = GenericRegistry("test-section-content", project_root=isolated_project_env)
        content = registry.compose("ENTRY", packs=[])

        assert content is not None
        assert "Introduction section." in str(content)

    def test_compose_returns_none_for_missing(
        self, isolated_project_env: Path
    ) -> None:
        """compose() returns None for non-existent entities."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry("roots", project_root=isolated_project_env)
        content = registry.compose("NONEXISTENT", packs=[])

        assert content is None


class TestGenericRegistryStrategyConfig:
    """Tests for strategy config loading from composition.yaml."""

    def test_loads_strategy_config_from_yaml(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry loads strategy config from composition.yaml."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Create composition.yaml
        config_dir = isolated_project_env / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "composition.yaml").write_text(
            """
composition:
  content_types:
    roots:
      dedupe: true
      known_sections:
        - intro
"""
        )

        registry = GenericRegistry("roots", project_root=isolated_project_env)
        config = registry.get_strategy_config()

        assert config["enable_dedupe"] is True
        assert config["enable_sections"] is True  # because known_sections is non-empty

    def test_default_config_when_no_yaml(self, isolated_project_env: Path) -> None:
        """GenericRegistry uses defaults when content_type not in YAML."""
        from edison.core.composition.registries.generic import GenericRegistry

        registry = GenericRegistry(
            "unknown-type", project_root=isolated_project_env
        )
        config = registry.get_strategy_config()

        # Should have sensible defaults
        assert "enable_sections" in config
        assert "enable_dedupe" in config
        assert config["enable_template_processing"] is True


class TestGenericRegistryWriteAll:
    """Tests for write_all() batch writing method."""

    def test_write_all_writes_all_entities(
        self, isolated_project_env: Path
    ) -> None:
        """write_all() composes and writes all entities to output dir."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid conflict with bundled content
        content_dir = isolated_project_env / ".edison" / "test-write-all"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "ENTRY1.md").write_text("# ENTRY1\n\nEntry1 content.\n")
        (content_dir / "ENTRY2.md").write_text("# ENTRY2\n\nEntry2 content.\n")

        # Create output directory
        output_dir = isolated_project_env / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        registry = GenericRegistry("test-write-all", project_root=isolated_project_env)
        written = registry.write_all(output_dir, packs=[])

        assert len(written) == 2
        assert (output_dir / "ENTRY1.md").exists()
        assert (output_dir / "ENTRY2.md").exists()
        assert "Entry1 content." in (output_dir / "ENTRY1.md").read_text()

    def test_write_all_returns_written_paths(
        self, isolated_project_env: Path
    ) -> None:
        """write_all() returns list of written file paths."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use unique content_type to avoid core bundled files
        content_dir = isolated_project_env / ".edison" / "test-unique-write"
        content_dir.mkdir(parents=True, exist_ok=True)
        (content_dir / "README.md").write_text("# README\n")

        output_dir = isolated_project_env / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        registry = GenericRegistry("test-unique-write", project_root=isolated_project_env)
        written = registry.write_all(output_dir, packs=[])

        assert len(written) == 1
        assert written[0] == output_dir / "README.md"


class TestGenericRegistryRootsUseCase:
    """Tests for the specific 'roots' use case (canonical → roots migration)."""

    def test_roots_registry_discovers_bundled_agents_md(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry('roots') discovers bundled AGENTS.md entry point."""
        from edison.core.composition.registries.generic import GenericRegistry

        # The bundled data/roots/AGENTS.md should be discovered
        registry = GenericRegistry("roots", project_root=isolated_project_env)
        names = registry.list_names()

        # Bundled core should have AGENTS
        assert "AGENTS" in names

    def test_roots_compose_uses_bundled_content(
        self, isolated_project_env: Path
    ) -> None:
        """GenericRegistry('roots') composes bundled content correctly."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Use the bundled data/roots/AGENTS.md
        registry = GenericRegistry("roots", project_root=isolated_project_env)
        content = registry.compose("AGENTS", packs=[])

        assert content is not None
        # Bundled content should be composed
        assert "Edison" in str(content) or "constitution" in str(content).lower()
