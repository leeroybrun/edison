from __future__ import annotations

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

    # User dir is forced to <tmp>/.edison-user by tests/conftest.py
    assert ctx.user_dir.resolve() == (root / ".edison-user").resolve()
    assert ctx.user_config_dir.resolve() == (root / ".edison-user" / "config").resolve()

    # Pack roots are deterministic precedence: bundled → user → project
    assert [r.kind for r in ctx.pack_roots] == ["bundled", "user", "project"]
    assert ctx.user_packs_dir.resolve() == (root / ".edison-user" / "packs").resolve()
    assert ctx.project_packs_dir.resolve() == (root / ".edison" / "packs").resolve()

