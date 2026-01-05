from __future__ import annotations

import os
from pathlib import Path

from edison.core.composition.registries.generic import GenericRegistry


def test_user_layer_can_add_new_guidelines(isolated_project_env: Path) -> None:
    """User-layer guidelines (~/.edison/guidelines) are discoverable and composable."""
    root = isolated_project_env
    user_root = Path(os.environ["EDISON_paths__user_config_dir"]).resolve()

    user_guideline = user_root / "guidelines" / "HELLO.md"
    user_guideline.parent.mkdir(parents=True, exist_ok=True)
    user_guideline.write_text("# Hello from user\n", encoding="utf-8")

    registry = GenericRegistry("guidelines", project_root=root)
    names = registry.list_names(packs=[])
    assert "HELLO" in names


def test_user_layer_can_overlay_core_guideline(isolated_project_env: Path) -> None:
    """User overlays apply after packs and before project overrides."""
    root = isolated_project_env
    user_root = Path(os.environ["EDISON_paths__user_config_dir"]).resolve()

    # Overlay a known core guideline.
    overlay = user_root / "guidelines" / "overlays" / "shared" / "VALIDATION.md"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text("User overlay line\n", encoding="utf-8")

    registry = GenericRegistry("guidelines", project_root=root)
    composed = registry.compose("shared/VALIDATION", packs=[])
    assert composed is not None
    assert "User overlay line" in composed
