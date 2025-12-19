from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.session.worktree.manager import _run_post_install_commands


def test_post_install_commands_run_in_worktree(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir(parents=True, exist_ok=True)

    _run_post_install_commands(
        worktree_path=worktree,
        commands=["echo ok > post-install.txt"],
        timeout=10,
    )

    assert (worktree / "post-install.txt").read_text(encoding="utf-8").strip() == "ok"


def test_post_install_commands_fail_closed(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir(parents=True, exist_ok=True)

    with pytest.raises(RuntimeError) as exc:
        _run_post_install_commands(
            worktree_path=worktree,
            commands=["exit 7"],
            timeout=10,
        )

    msg = str(exc.value)
    assert "Post-install command failed" in msg
    assert "exit: 7" in msg
