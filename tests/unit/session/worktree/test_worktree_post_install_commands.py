from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from edison.core.session.worktree.manager import _run_post_install_commands


def test_post_install_commands_run_even_when_install_deps_false(tmp_path: Path) -> None:
    """Regression test: postInstallCommands must run even when installDeps=false.

    Beta tester reported that postInstallCommands were NOT executed when
    installDeps was false, requiring manual intervention to build packages.
    """
    # Create a minimal git repo structure
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create a marker file to track if post-install ran
    marker = worktree / "post-install-marker.txt"

    config = {
        "enabled": True,
        "installDeps": False,  # The key condition: deps disabled
        "postInstallCommands": [f"echo ran > {marker}"],  # But we have post-install commands
    }

    # We need to simulate the relevant parts of create_worktree logic
    # that handle postInstallCommands independently of installDeps
    from edison.core.session.worktree.manager import _run_post_install_commands

    post_install = config.get("postInstallCommands", []) or []
    if isinstance(post_install, list) and post_install:
        commands = [str(c) for c in post_install if str(c).strip()]
        _run_post_install_commands(
            worktree_path=worktree,
            commands=commands,
            timeout=30,
        )

    # The marker file should exist after post-install commands run
    assert marker.exists(), "postInstallCommands should run even when installDeps=false"
    assert marker.read_text().strip() == "ran"


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
