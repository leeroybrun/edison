"""Tests for vendor external roots in CompositionPathResolver.

Vendor external roots expose vendor checkout directories to the composition
system so they can participate in layered content discovery.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestCompositionPathResolverVendorRoots:
    """Test CompositionPathResolver vendor root discovery."""

    def test_vendor_roots_returns_empty_when_no_vendors_configured(
        self, tmp_path: Path
    ) -> None:
        """vendor_roots should return empty list when no vendors.yaml."""
        from edison.core.composition.core.paths import CompositionPathResolver

        # Create minimal project structure without vendors.yaml
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        resolver = CompositionPathResolver(repo_root=tmp_path)
        vendor_roots = resolver.vendor_roots

        assert vendor_roots == []

    def test_vendor_roots_returns_configured_vendor_paths(
        self, tmp_path: Path
    ) -> None:
        """vendor_roots should return paths from vendors.yaml configuration."""
        from edison.core.composition.core.paths import CompositionPathResolver

        # Create project with vendor config
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

        # Create the vendor checkout
        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_path.mkdir(parents=True)

        resolver = CompositionPathResolver(repo_root=tmp_path)
        vendor_roots = resolver.vendor_roots

        assert len(vendor_roots) == 1
        assert vendor_roots[0][0] == "opencode"
        assert vendor_roots[0][1] == vendor_path

    def test_vendor_roots_skips_non_existent_vendor_checkouts(
        self, tmp_path: Path
    ) -> None:
        """vendor_roots should skip vendors whose path doesn't exist."""
        from edison.core.composition.core.paths import CompositionPathResolver

        # Create project with vendor config but no checkout
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
        # Note: vendor checkout NOT created

        resolver = CompositionPathResolver(repo_root=tmp_path)
        vendor_roots = resolver.vendor_roots

        assert vendor_roots == []

    def test_vendor_roots_skips_vendor_paths_that_are_files(self, tmp_path: Path) -> None:
        """vendor_roots should ignore configured vendor paths that aren't directories."""
        from edison.core.composition.core.paths import CompositionPathResolver

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

        # Create a file at the vendor path (not a directory)
        vendor_path = tmp_path / "vendors"
        vendor_path.mkdir(parents=True)
        (vendor_path / "opencode").write_text("not a directory", encoding="utf-8")

        resolver = CompositionPathResolver(repo_root=tmp_path)
        assert resolver.vendor_roots == []

    def test_vendor_roots_returns_multiple_vendors_in_config_order(
        self, tmp_path: Path
    ) -> None:
        """vendor_roots should preserve vendor order from config."""
        from edison.core.composition.core.paths import CompositionPathResolver

        (tmp_path / ".edison" / "config").mkdir(parents=True)
        write_yaml(
            tmp_path / ".edison" / "config" / "vendors.yaml",
            """
            vendors:
              sources:
                - name: vendor-a
                  url: https://example.com/a.git
                  ref: main
                  path: vendors/vendor-a
                - name: vendor-b
                  url: https://example.com/b.git
                  ref: main
                  path: vendors/vendor-b
            """,
        )

        # Create vendor checkouts
        (tmp_path / "vendors" / "vendor-a").mkdir(parents=True)
        (tmp_path / "vendors" / "vendor-b").mkdir(parents=True)

        resolver = CompositionPathResolver(repo_root=tmp_path)
        vendor_roots = resolver.vendor_roots

        assert len(vendor_roots) == 2
        assert vendor_roots[0][0] == "vendor-a"
        assert vendor_roots[1][0] == "vendor-b"


class TestLayerContextVendorRoots:
    """Test LayerContext includes vendor roots."""

    def test_layer_context_includes_vendor_roots(self, tmp_path: Path) -> None:
        """LayerContext should include vendor_roots tuple."""
        from edison.core.composition.core.paths import CompositionPathResolver

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
        (tmp_path / "vendors" / "opencode").mkdir(parents=True)

        resolver = CompositionPathResolver(repo_root=tmp_path)
        ctx = resolver.layer_context

        assert hasattr(ctx, "vendor_roots")
        assert len(ctx.vendor_roots) == 1
        assert ctx.vendor_roots[0][0] == "opencode"
