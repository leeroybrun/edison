from __future__ import annotations

from pathlib import Path


def test_layer_discovery_preserves_nested_relative_paths(tmp_path: Path) -> None:
    """LayerDiscovery must preserve subdirectories in entity keys.

    This enables composing into structured `_generated/**` trees and avoids
    collisions between same-named files in different subfolders.
    """
    from edison.core.composition.core.discovery import LayerDiscovery

    core_dir = tmp_path / "core"
    packs_dir = tmp_path / "packs"
    project_dir = tmp_path / "project"

    # Core content: <core>/<type>/<nested>/<file>.md
    (core_dir / "guidelines" / "shared").mkdir(parents=True, exist_ok=True)
    (core_dir / "guidelines" / "shared" / "TDD.md").write_text("# TDD\n", encoding="utf-8")

    ld = LayerDiscovery(
        content_type="guidelines",
        core_dir=core_dir,
        pack_roots=[("bundled", packs_dir)],
        user_dir=tmp_path / "user",
        project_dir=project_dir,
        file_pattern="*.md",
    )

    core = ld.discover_core()
    assert "shared/TDD" in core
    assert core["shared/TDD"].path.name == "TDD.md"


def test_layer_discovery_supports_nested_project_overlays(tmp_path: Path) -> None:
    """Project overlays under overlays/** should support arbitrary nesting."""
    from edison.core.composition.core.discovery import LayerDiscovery

    core_dir = tmp_path / "core"
    packs_dir = tmp_path / "packs"
    project_dir = tmp_path / "project"

    # Seed existing with a nested core file.
    (core_dir / "guidelines" / "orchestrators").mkdir(parents=True, exist_ok=True)
    (core_dir / "guidelines" / "orchestrators" / "SESSION_WORKFLOW.md").write_text(
        "# SESSION_WORKFLOW\n",
        encoding="utf-8",
    )

    # Matching nested project overlay:
    overlays_dir = project_dir / "guidelines" / "overlays" / "orchestrators"
    overlays_dir.mkdir(parents=True, exist_ok=True)
    (overlays_dir / "SESSION_WORKFLOW.md").write_text(
        "# SESSION_WORKFLOW\n\nProject overlay.\n",
        encoding="utf-8",
    )

    ld = LayerDiscovery(
        content_type="guidelines",
        core_dir=core_dir,
        pack_roots=[("bundled", packs_dir)],
        user_dir=tmp_path / "user",
        project_dir=project_dir,
        file_pattern="*.md",
    )

    existing = set(ld.discover_core().keys())
    overlays = ld.discover_project_overlays(existing)

    assert "orchestrators/SESSION_WORKFLOW" in overlays







