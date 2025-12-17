from __future__ import annotations

from pathlib import Path

from edison.core.context.files import FileContextService
from edison.core.session.core.models import Session
from edison.core.session.persistence.repository import SessionRepository
from edison.core.utils.subprocess import run_with_timeout


def test_file_context_service_uses_session_base_branch(isolated_project_env: Path) -> None:
    """When a session is based on a non-main branch, file detection must diff against that base.

    Real projects often use a non-`main` base branch for Edison worktrees. If we always diff
    against `main`, the "modifiedFiles" set explodes to include the entire divergence, which
    triggers irrelevant validators and bloats context.
    """
    repo = isolated_project_env

    # Create a branch that diverges from main with an extra file.
    run_with_timeout(
        ["git", "checkout", "-b", "base-feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    (repo / "feature.txt").write_text("base feature\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "feature.txt"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "base feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Return to main (primary checkout).
    run_with_timeout(
        ["git", "checkout", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Create a session worktree branch starting from the diverged base branch.
    session_id = "sid-base-branch"
    worktrees_dir = repo / ".worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    wt_path = worktrees_dir / session_id
    run_with_timeout(
        ["git", "worktree", "add", "-b", f"session/{session_id}", str(wt_path), "base-feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Add a session-specific commit on top of base-feature.
    (wt_path / "session-change.txt").write_text("session change\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "session-change.txt"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "session change"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Persist session metadata (including its real base branch) so FileContextService can read it.
    session = Session.create(session_id, owner="test", state="active")
    session.git.base_branch = "base-feature"
    session.git.branch_name = f"session/{session_id}"
    session.git.worktree_path = str(wt_path)
    SessionRepository(project_root=repo).create(session)

    ctx = FileContextService(project_root=repo).get_for_session(session_id)
    assert "session-change.txt" in ctx.all_files
    assert "feature.txt" not in ctx.all_files

