from __future__ import annotations

from pathlib import Path

import pytest


def test_build_layer_dirs_includes_user_layers() -> None:
    from edison.core.utils.loader import build_layer_dirs

    core_dir = Path("/core")
    bundled_packs_dir = Path("/bundled_packs")
    user_packs_dir = Path("/user_packs")
    project_packs_dir = Path("/project_packs")
    user_dir = Path("/user")
    project_dir = Path("/project")

    dirs = build_layer_dirs(
        core_dir=core_dir,
        content_type="guards",
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        user_dir=user_dir,
        project_dir=project_dir,
        active_packs=["a", "b"],
    )

    assert dirs == [
        core_dir / "guards",
        bundled_packs_dir / "a" / "guards",
        bundled_packs_dir / "b" / "guards",
        user_packs_dir / "a" / "guards",
        user_packs_dir / "b" / "guards",
        project_packs_dir / "a" / "guards",
        project_packs_dir / "b" / "guards",
        user_dir / "guards",
        project_dir / "guards",
    ]

