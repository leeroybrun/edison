from __future__ import annotations

import subprocess
from pathlib import Path


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_remove_worktree_refuses_to_delete_non_session_branch(session_git_repo_path: Path, tmp_path: Path) -> None:
    from edison.core.session.worktree.cleanup import remove_worktree

    repo = session_git_repo_path

    # Create a non-session branch that must never be deleted by worktree cleanup helpers.
    _git(repo, "branch", "feature/no-delete")
    assert _git(repo, "show-ref", "--verify", "refs/heads/feature/no-delete").returncode == 0

    remove_worktree(tmp_path / "does-not-exist", branch_name="feature/no-delete")

    # Branch must still exist.
    assert _git(repo, "show-ref", "--verify", "refs/heads/feature/no-delete").returncode == 0


def test_remove_worktree_deletes_session_branch(session_git_repo_path: Path, tmp_path: Path) -> None:
    from edison.core.session.worktree.cleanup import remove_worktree

    repo = session_git_repo_path
    _git(repo, "branch", "session/sess-delete-ok")
    assert _git(repo, "show-ref", "--verify", "refs/heads/session/sess-delete-ok").returncode == 0

    remove_worktree(tmp_path / "does-not-exist", branch_name="session/sess-delete-ok")

    assert _git(repo, "show-ref", "--verify", "refs/heads/session/sess-delete-ok").returncode != 0
