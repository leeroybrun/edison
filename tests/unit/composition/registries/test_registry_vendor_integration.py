"""Tests for ComposableRegistry vendor integration.

Vendor content should participate in the composition layering system.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    """Helper to write file content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestComposableRegistryVendorDiscovery:
    """Test ComposableRegistry vendor content discovery."""

    def test_registry_discovery_includes_vendor_roots(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Registry discovery should use vendor roots from path resolver."""
        from edison.core.composition.registries._base import ComposableRegistry
        from edison.core.composition.core.discovery import LayerDiscovery

        # Set up project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        # Create vendor content
        vendor_content = tmp_path / "vendors" / "opencode" / "skills"
        vendor_content.mkdir(parents=True)
        write_file(
            vendor_content / "vendor-skill.md",
            """
            # Vendor Skill

            This skill is from a vendor.
            """,
        )

        # Create a test registry
        class TestRegistry(ComposableRegistry[str]):
            content_type = "skills"
            file_pattern = "*.md"

        # Patch project root resolution
        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        registry = TestRegistry(project_root=tmp_path)

        # The discovery should have vendor roots
        assert hasattr(registry.discovery, "vendor_roots")
        assert len(registry.discovery.vendor_roots) == 1
        assert registry.discovery.vendor_roots[0][0] == "opencode"


class TestComposableRegistryVendorComposition:
    """Test ComposableRegistry composes vendor content."""

    def test_vendor_content_included_in_composition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Vendor content should be included when composing entities."""
        from edison.core.composition.registries.generic import GenericRegistry

        # Set up project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/example/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        # Create vendor content with new skill
        vendor_content = tmp_path / "vendors" / "opencode" / "skills"
        vendor_content.mkdir(parents=True)
        write_file(
            vendor_content / "vendor-skill.md",
            """
            # Vendor Skill

            Skill content from vendor.
            """,
        )

        # Patch project root and bundled data path
        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        registry = GenericRegistry(
            content_type="skills",
            file_pattern="*.md",
            project_root=tmp_path,
        )

        # Vendor skill should be discoverable
        all_entities = registry.discover_all(packs=[])
        assert "vendor-skill" in all_entities

    def test_vendor_overlay_extends_core_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Vendor overlays should extend core content."""
        from edison.core.composition.core.discovery import LayerDiscovery
        from edison.core.composition.strategies import CompositionContext, LayerContent, MarkdownCompositionStrategy

        # Set up project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/example/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        # Mock core dir content
        mock_core = tmp_path / "mock_core"
        (mock_core / "skills").mkdir(parents=True)
        write_file(
            mock_core / "skills" / "tdd.md",
            """
            # TDD

            <!-- SECTION: intro -->
            Core TDD intro.
            <!-- /SECTION: intro -->
            """,
        )

        # Create vendor overlay for existing core content
        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_overlays = vendor_path / "skills" / "overlays"
        vendor_overlays.mkdir(parents=True)
        write_file(
            vendor_overlays / "tdd.md",
            """
            <!-- EXTEND: intro -->

            Vendor extension for TDD skill.
            <!-- /EXTEND -->
            """,
        )

        # Use LayerDiscovery directly to test the composition
        ld = LayerDiscovery(
            content_type="skills",
            core_dir=mock_core,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=[("opencode", vendor_path)],
        )

        # Discover entities
        core_entities = ld.discover_core()
        assert "tdd" in core_entities

        existing = set(core_entities.keys())
        vendor_overlays_map = ld.discover_vendor_overlays(existing)
        assert "tdd" in vendor_overlays_map

        # Compose layers
        layers = [
            LayerContent(
                content=(mock_core / "skills" / "tdd.md").read_text(),
                source="core",
                path=mock_core / "skills" / "tdd.md",
            ),
            LayerContent(
                content=vendor_overlays_map["tdd"].path.read_text(),
                source="vendor:opencode",
                path=vendor_overlays_map["tdd"].path,
            ),
        ]

        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
        )
        ctx = CompositionContext(
            active_packs=[],
            config={},
            project_root=tmp_path,
            source_dir=mock_core,
        )
        composed = strategy.compose(layers, ctx)

        assert "Vendor extension for TDD skill" in composed
        assert "Core TDD intro" in composed


class TestVendorIncludeResolution:
    """Test that {{include:...}} can resolve vendor-exported entities."""

    def test_include_resolves_vendor_entity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Include provider should resolve vendor entities via content_path mapping.

        When a pack/project template uses {{include:skills/vendor-skill}}, it should
        resolve to the vendor-exported skill content if that entity is provided by
        a vendor.
        """
        from edison.core.composition.registries.generic import GenericRegistry

        # Set up project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/example/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        # Create vendor content
        vendor_content = tmp_path / "vendors" / "opencode" / "skills"
        vendor_content.mkdir(parents=True)
        write_file(
            vendor_content / "test-driven-development.md",
            """
            # Test-Driven Development

            This is vendor-exported TDD content.
            """,
        )

        # Patch project root
        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        # Create registry
        registry = GenericRegistry(
            content_type="skills",
            file_pattern="*.md",
            project_root=tmp_path,
        )

        # Verify vendor entity is discoverable
        all_entities = registry.discover_all(packs=[])
        assert "test-driven-development" in all_entities

        # Compose the vendor entity
        composed = registry.compose("test-driven-development", packs=[])
        assert composed is not None
        assert "This is vendor-exported TDD content" in composed

    def test_vendor_entity_included_via_template(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Template with {{include:skills/entity}} should include vendor content.

        This tests the full include resolution flow where a wrapper template
        includes vendor-exported content via the standard include syntax.
        """
        from edison.core.composition.core.discovery import LayerDiscovery
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )
        from edison.core.composition.engine import TemplateEngine

        # Set up project structure
        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/example/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        # Mock core dir
        mock_core = tmp_path / "mock_core"
        (mock_core / "skills").mkdir(parents=True)

        # Create vendor content
        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_skills = vendor_path / "skills"
        vendor_skills.mkdir(parents=True)
        write_file(
            vendor_skills / "vendor-skill.md",
            """
            Vendor skill content that should be included.
            """,
        )

        # Patch project root
        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        # Create discovery with vendor roots
        ld = LayerDiscovery(
            content_type="skills",
            core_dir=mock_core,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=[("opencode", vendor_path)],
        )

        # Verify vendor content is discovered
        vendor_layers = ld.iter_vendor_layers(set())
        assert len(vendor_layers) == 1
        _, vendor_new, _ = vendor_layers[0]
        assert "vendor-skill" in vendor_new

        # Create a simple include provider that resolves vendor entities
        def include_provider(path: str) -> str | None:
            # Simulate content_path matching for "skills/..."
            if path.startswith("skills/"):
                entity_name = path.replace("skills/", "").replace(".md", "")
                if entity_name == "vendor-skill":
                    return "Vendor skill content that should be included."
            return None

        # Create template that includes vendor content
        template = """# Wrapper

## Included from vendor:
{{include:skills/vendor-skill}}

## End wrapper
"""

        # Process template
        engine = TemplateEngine(
            config={},
            packs=[],
            project_root=tmp_path,
            source_dir=mock_core,
            include_provider=include_provider,
        )
        result, _ = engine.process(template)

        assert "Vendor skill content that should be included" in result
        assert "# Wrapper" in result
        assert "## End wrapper" in result
