"""Tests for vendor discovery caching and existing-set behavior."""

from __future__ import annotations

from pathlib import Path

from edison.core.composition.core.discovery import LayerDiscovery


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_core_returns_cached_map_instance(tmp_path: Path) -> None:
    """Repeated discovery calls should reuse cached dicts (no full-map copies)."""
    core_dir = tmp_path / "core"
    _write(core_dir / "guidelines" / "a.md")

    ld = LayerDiscovery(
        content_type="guidelines",
        core_dir=core_dir,
        pack_roots=[],
        overlay_layers=[],
        vendor_roots=[],
    )

    first = ld.discover_core()
    second = ld.discover_core()
    assert first is second
    assert "a" in first


def test_discover_vendor_updates_existing_set_for_overlay_validation(tmp_path: Path) -> None:
    """discover_vendor should add vendor-defined entities to existing for overlays."""
    core_dir = tmp_path / "core"
    vendor_root = tmp_path / "vendor-opencode"

    # Vendor defines a new entity and then overlays it.
    _write(vendor_root / "guidelines" / "bar.md")
    _write(vendor_root / "guidelines" / "overlays" / "bar.md", content="overlay")

    ld = LayerDiscovery(
        content_type="guidelines",
        core_dir=core_dir,
        pack_roots=[],
        overlay_layers=[],
        vendor_roots=[("opencode", vendor_root)],
    )

    existing: set[str] = set()
    vendor_new = ld.discover_vendor(existing)
    assert "bar" in vendor_new
    assert "bar" in existing

    vendor_overlays = ld.discover_vendor_overlays(existing)
    assert "bar" in vendor_overlays

