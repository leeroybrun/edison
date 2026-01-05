from __future__ import annotations

import os
from pathlib import Path

from edison.core.composition.core.paths import CompositionPathResolver


def test_layer_context_exposes_config_dirs(isolated_project_env: Path) -> None:
    root = isolated_project_env

    resolver = CompositionPathResolver(root)
    ctx = resolver.layer_context

    assert ctx.repo_root.resolve() == root.resolve()
    assert ctx.project_dir.resolve() == (root / ".edison").resolve()
    assert ctx.project_config_dir.resolve() == (root / ".edison" / "config").resolve()
    assert ctx.project_local_config_dir.resolve() == (root / ".edison" / "config.local").resolve()

    # User dir is forced by tests/conftest.py and should not be hardcoded to live
    # under the repo root (to avoid polluting git status).
    expected_user_dir = Path(os.environ["EDISON_paths__user_config_dir"]).resolve()
    assert ctx.user_dir.resolve() == expected_user_dir
    assert ctx.user_config_dir.resolve() == (expected_user_dir / "config").resolve()

    # Pack roots are deterministic precedence: bundled → user → project
    assert [r.kind for r in ctx.pack_roots] == ["bundled", "user", "project"]
    assert ctx.user_packs_dir.resolve() == (expected_user_dir / "packs").resolve()
    assert ctx.project_packs_dir.resolve() == (root / ".edison" / "packs").resolve()
