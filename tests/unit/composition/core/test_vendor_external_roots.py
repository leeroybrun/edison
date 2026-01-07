"""Tests for vendor external root discovery in composition.

Vendor external roots enable external vendor checkouts to participate in
Edison's layered composition system.

Discovery precedence: core < vendors < packs < overlay layers
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestLayerDiscoveryVendorRoots:
    """Test LayerDiscovery vendor external root support."""

    def test_layer_discovery_accepts_vendor_roots_parameter(self, tmp_path: Path) -> None:
        """LayerDiscovery should accept vendor_roots parameter."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        core_dir.mkdir()

        # Vendor roots are (vendor_name, path) tuples
        vendor_roots = [("opencode", tmp_path / "vendors" / "opencode")]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        assert hasattr(ld, "vendor_roots")
        assert len(ld.vendor_roots) == 1
        assert ld.vendor_roots[0][0] == "opencode"

    def test_discover_vendor_entities_returns_entities_from_vendor_roots(
        self, tmp_path: Path
    ) -> None:
        """discover_vendor should return entities from vendor external roots."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        core_dir.mkdir()

        # Create vendor with skills content
        vendor_path = tmp_path / "vendors" / "opencode"
        skill_dir = vendor_path / "skills" / "testing"
        skill_dir.mkdir(parents=True)
        (skill_dir / "test-driven-development.md").write_text(
            "# TDD Skill\n\nFrom vendor.\n", encoding="utf-8"
        )

        vendor_roots = [("opencode", vendor_path)]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        vendor_entities = ld.discover_vendor()

        assert "testing/test-driven-development" in vendor_entities
        assert vendor_entities["testing/test-driven-development"].layer == "vendor:opencode"
        assert vendor_entities["testing/test-driven-development"].is_overlay is False

    def test_discover_vendor_does_not_follow_symlinks_outside_vendor_root(
        self, tmp_path: Path
    ) -> None:
        """Vendor discovery should not traverse symlinks that escape the vendor root."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        core_dir.mkdir()

        vendor_path = tmp_path / "vendors" / "opencode"
        (vendor_path / "skills").mkdir(parents=True)

        outside_dir = tmp_path / "outside" / "skills"
        outside_dir.mkdir(parents=True)
        (outside_dir / "leak.md").write_text("# Leak\n", encoding="utf-8")

        # Symlink inside the vendor tree pointing outside.
        (vendor_path / "skills" / "outside").symlink_to(outside_dir, target_is_directory=True)

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=[("opencode", vendor_path)],
        )

        vendor_entities = ld.discover_vendor()
        assert "leak" not in vendor_entities

    def test_vendor_discovery_order_is_core_then_vendors_then_packs(
        self, tmp_path: Path
    ) -> None:
        """Vendor entities should be discovered after core but before packs.

        Discovery order: core < vendors < packs < overlay layers
        """
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        packs_dir = tmp_path / "packs"
        vendor_path = tmp_path / "vendors" / "opencode"

        # Create same entity in core
        (core_dir / "skills").mkdir(parents=True)
        (core_dir / "skills" / "common-skill.md").write_text(
            "# Core skill\n", encoding="utf-8"
        )

        # Create same entity in vendor (should NOT shadow core - no allow_shadowing)
        (vendor_path / "skills").mkdir(parents=True)
        (vendor_path / "skills" / "common-skill.md").write_text(
            "# Vendor skill\n", encoding="utf-8"
        )

        vendor_roots = [("opencode", vendor_path)]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[("bundled", packs_dir)],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
            allow_shadowing=False,
        )

        # Discover core first
        core_entities = ld.discover_core()
        assert "common-skill" in core_entities

        # Vendor entities that shadow core should raise
        from edison.core.composition.core.errors import CompositionValidationError

        with pytest.raises(CompositionValidationError, match="shadows"):
            ld.discover_vendor(existing=set(core_entities.keys()))

    def test_vendor_new_entities_added_to_existing_set(self, tmp_path: Path) -> None:
        """New vendor entities should expand the existing entity set."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        vendor_path = tmp_path / "vendors" / "opencode"

        # Core entity
        (core_dir / "skills").mkdir(parents=True)
        (core_dir / "skills" / "core-skill.md").write_text(
            "# Core\n", encoding="utf-8"
        )

        # New vendor entity (not in core)
        (vendor_path / "skills").mkdir(parents=True)
        (vendor_path / "skills" / "vendor-skill.md").write_text(
            "# Vendor\n", encoding="utf-8"
        )

        vendor_roots = [("opencode", vendor_path)]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        existing = set(ld.discover_core().keys())
        assert "core-skill" in existing
        assert "vendor-skill" not in existing

        vendor_entities = ld.discover_vendor(existing=existing)
        assert "vendor-skill" in vendor_entities


class TestLayerDiscoveryVendorOverlays:
    """Test vendor overlay support."""

    def test_vendor_overlays_extend_core_entities(self, tmp_path: Path) -> None:
        """Vendor overlays should be able to extend core entities."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        vendor_path = tmp_path / "vendors" / "opencode"

        # Core entity
        (core_dir / "skills").mkdir(parents=True)
        (core_dir / "skills" / "tdd.md").write_text(
            "# TDD\n\nCore content.\n", encoding="utf-8"
        )

        # Vendor overlay for core entity
        overlay_dir = vendor_path / "skills" / "overlays"
        overlay_dir.mkdir(parents=True)
        (overlay_dir / "tdd.md").write_text(
            "<!-- EXTEND intro -->\n\nVendor extension.\n", encoding="utf-8"
        )

        vendor_roots = [("opencode", vendor_path)]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        existing = set(ld.discover_core().keys())
        vendor_overlays = ld.discover_vendor_overlays(existing=existing)

        assert "tdd" in vendor_overlays
        assert vendor_overlays["tdd"].is_overlay is True
        assert vendor_overlays["tdd"].layer == "vendor:opencode"


class TestLayerDiscoveryMultipleVendors:
    """Test multiple vendor root handling."""

    def test_multiple_vendors_discovered_in_order(self, tmp_path: Path) -> None:
        """Multiple vendors should be discovered in provided order."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        core_dir.mkdir()

        # Vendor 1
        vendor1 = tmp_path / "vendors" / "vendor1"
        (vendor1 / "skills").mkdir(parents=True)
        (vendor1 / "skills" / "skill-a.md").write_text("# A\n", encoding="utf-8")

        # Vendor 2
        vendor2 = tmp_path / "vendors" / "vendor2"
        (vendor2 / "skills").mkdir(parents=True)
        (vendor2 / "skills" / "skill-b.md").write_text("# B\n", encoding="utf-8")

        vendor_roots = [
            ("vendor1", vendor1),
            ("vendor2", vendor2),
        ]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        vendor_entities = ld.discover_vendor()

        assert "skill-a" in vendor_entities
        assert "skill-b" in vendor_entities
        assert vendor_entities["skill-a"].layer == "vendor:vendor1"
        assert vendor_entities["skill-b"].layer == "vendor:vendor2"

    def test_later_vendor_cannot_shadow_earlier_vendor(self, tmp_path: Path) -> None:
        """Later vendors should not shadow entities from earlier vendors."""
        from edison.core.composition.core.discovery import LayerDiscovery
        from edison.core.composition.core.errors import CompositionValidationError

        core_dir = tmp_path / "core"
        core_dir.mkdir()

        # Vendor 1 defines a skill
        vendor1 = tmp_path / "vendors" / "vendor1"
        (vendor1 / "skills").mkdir(parents=True)
        (vendor1 / "skills" / "shared-skill.md").write_text("# V1\n", encoding="utf-8")

        # Vendor 2 tries to define same skill
        vendor2 = tmp_path / "vendors" / "vendor2"
        (vendor2 / "skills").mkdir(parents=True)
        (vendor2 / "skills" / "shared-skill.md").write_text("# V2\n", encoding="utf-8")

        vendor_roots = [
            ("vendor1", vendor1),
            ("vendor2", vendor2),
        ]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
            allow_shadowing=False,
        )

        with pytest.raises(CompositionValidationError, match="shadows"):
            ld.discover_vendor()


class TestIterVendorLayers:
    """Test iter_vendor_layers method for bulk vendor discovery."""

    def test_iter_vendor_layers_returns_new_and_overlay_maps(
        self, tmp_path: Path
    ) -> None:
        """iter_vendor_layers should yield (vendor_name, new, overlays) tuples."""
        from edison.core.composition.core.discovery import LayerDiscovery

        core_dir = tmp_path / "core"
        vendor_path = tmp_path / "vendors" / "opencode"

        # Core
        (core_dir / "skills").mkdir(parents=True)
        (core_dir / "skills" / "core-skill.md").write_text("# Core\n", encoding="utf-8")

        # Vendor new
        (vendor_path / "skills").mkdir(parents=True)
        (vendor_path / "skills" / "vendor-skill.md").write_text(
            "# Vendor\n", encoding="utf-8"
        )

        # Vendor overlay
        overlay_dir = vendor_path / "skills" / "overlays"
        overlay_dir.mkdir(parents=True)
        (overlay_dir / "core-skill.md").write_text(
            "<!-- EXTEND -->\n\nExtension.\n", encoding="utf-8"
        )

        vendor_roots = [("opencode", vendor_path)]

        ld = LayerDiscovery(
            content_type="skills",
            core_dir=core_dir,
            pack_roots=[],
            overlay_layers=[],
            file_pattern="*.md",
            vendor_roots=vendor_roots,
        )

        existing = set(ld.discover_core().keys())
        layers = ld.iter_vendor_layers(existing)

        assert len(layers) == 1
        vendor_name, new_map, over_map = layers[0]

        assert vendor_name == "opencode"
        assert "vendor-skill" in new_map
        assert "core-skill" in over_map
