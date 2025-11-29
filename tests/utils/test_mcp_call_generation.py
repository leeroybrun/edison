from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.session import lifecycle as session_manager
from edison.core.session.lifecycle.manager import get_session
from edison.core.session.persistence.graph import save_session
from edison.core.utils import git as git_utils
from edison.core.utils.subprocess import run_with_timeout
from edison.core.utils.mcp import format_clink_cli_command, resolve_working_directory


@pytest.fixture()
def repo_with_commit(isolated_project_env: Path) -> Path:
    root = isolated_project_env
    (root / "README.md").write_text("base\n", encoding="utf-8")
    run_with_timeout(["git", "add", "README.md"], cwd=root, check=True)
    run_with_timeout(["git", "commit", "-m", "init"], cwd=root, check=True)
    run_with_timeout(["git", "branch", "-M", "main"], cwd=root, check=True)
    return root


def test_mcp_call_includes_working_directory_when_in_worktree(repo_with_commit: Path) -> None:
    repo_root = repo_with_commit
    session_id = "wt-session"
    branch = f"session/{session_id}"
    worktree_path = repo_root / ".worktrees" / session_id

    run_with_timeout(
        ["git", "worktree", "add", str(worktree_path), "-b", branch],
        cwd=repo_root,
        check=True,
    )
    assert git_utils.is_worktree(worktree_path) is True

    session_manager.create_session(session_id, owner="tester", create_wt=False)
    session = get_session(session_id)
    session.setdefault("git", {})["worktreePath"] = str(worktree_path)
    save_session(session_id, session)

    cmd = format_clink_cli_command(
        cli_name="codex",
        role="default",
        prompt="Write tests for worktree isolation",
        session_id=session_id,
    )

    assert "mcp__edison-zen__clink" in cmd
    assert "--working_directory" in cmd
    assert str(worktree_path) in cmd
    assert resolve_working_directory(session_id) == worktree_path


def test_mcp_call_without_working_directory_when_no_worktree(
    repo_with_commit: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = repo_with_commit
    monkeypatch.chdir(repo_root)

    assert git_utils.is_worktree(repo_root) is False

    cmd = format_clink_cli_command(
        cli_name="claude",
        role="validator",
        prompt="Validate output",
    )

    assert "--working_directory" not in cmd
    assert resolve_working_directory(None) is None
