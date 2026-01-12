from __future__ import annotations

from pathlib import Path

import pytest


def test_ensure_shared_paths_resolves_shared_root_once(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_shared_root() is expensive in meta mode; ensure it's cached per invocation."""
    from edison.core.session.worktree.manager.shared_paths import ensure_shared_paths_in_checkout
    from edison.core.session.worktree.config_helpers import _config

    cfg = _config().get_worktree_config()

    calls = {"n": 0}

    def _counting_resolve_shared_root(*, repo_dir: Path, cfg: dict) -> Path:  # type: ignore[no-redef]
        from edison.core.session.worktree.manager.shared_root import resolve_shared_root as real

        calls["n"] += 1
        return real(repo_dir=repo_dir, cfg=cfg)

    monkeypatch.setattr(
        "edison.core.session.worktree.manager.shared_paths.resolve_shared_root",
        _counting_resolve_shared_root,
    )

    # Use a minimal config with multiple shared paths to exercise the caching.
    test_cfg = {
        **cfg,
        "sharedState": {
            **(cfg.get("sharedState") or {}),
            "mode": "meta",
            "sharedPaths": [
                {"path": ".project/tasks", "scopes": ["session"]},
                {"path": ".project/qa", "scopes": ["session"]},
                {"path": ".edison/_generated", "scopes": ["session"]},
                {"path": ".codex", "scopes": ["session"]},
            ],
        },
    }

    ensure_shared_paths_in_checkout(
        checkout_path=isolated_project_env,
        repo_dir=isolated_project_env,
        cfg=test_cfg,
        scope="session",
    )

    assert calls["n"] == 1


def test_shared_paths_only_if_target_exists_skips_missing_target(
    isolated_project_env: Path,
) -> None:
    from edison.core.session.worktree.manager.shared_paths import ensure_shared_paths_in_checkout
    from edison.core.session.worktree.config_helpers import _config

    cfg = _config().get_worktree_config()
    checkout = isolated_project_env / "checkout"
    checkout.mkdir(parents=True, exist_ok=True)

    test_cfg = {
        **cfg,
        "sharedState": {
            "mode": "primary",
            "sharedPaths": [
                {
                    "path": ".venv",
                    "scopes": ["session"],
                    "type": "dir",
                    "targetRoot": "primary",
                    "mergeExisting": False,
                    "onlyIfTargetExists": True,
                }
            ],
        },
    }

    updated, skipped = ensure_shared_paths_in_checkout(
        checkout_path=checkout,
        repo_dir=isolated_project_env,
        cfg=test_cfg,
        scope="session",
    )
    assert updated == 0
    assert skipped == 0
    assert not (isolated_project_env / ".venv").exists()
    assert not (checkout / ".venv").exists()


def test_shared_paths_only_if_target_exists_links_when_target_present(
    isolated_project_env: Path,
) -> None:
    from edison.core.session.worktree.manager.shared_paths import ensure_shared_paths_in_checkout
    from edison.core.session.worktree.config_helpers import _config

    cfg = _config().get_worktree_config()
    checkout = isolated_project_env / "checkout2"
    checkout.mkdir(parents=True, exist_ok=True)

    target = isolated_project_env / ".venv"
    target.mkdir(parents=True, exist_ok=True)
    (target / "pyvenv.cfg").write_text("home = /usr/bin/python\n", encoding="utf-8")

    test_cfg = {
        **cfg,
        "sharedState": {
            "mode": "primary",
            "sharedPaths": [
                {
                    "path": ".venv",
                    "scopes": ["session"],
                    "type": "dir",
                    "targetRoot": "primary",
                    "mergeExisting": False,
                    "onlyIfTargetExists": True,
                }
            ],
        },
    }

    updated, skipped = ensure_shared_paths_in_checkout(
        checkout_path=checkout,
        repo_dir=isolated_project_env,
        cfg=test_cfg,
        scope="session",
    )
    assert updated == 1
    assert skipped == 0
    link = checkout / ".venv"
    assert link.is_symlink()
    assert link.resolve() == target.resolve()
