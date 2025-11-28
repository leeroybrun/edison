from __future__ import annotations

from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout


def _init_git_repo(repo_root: Path) -> None:
    """Create a real git repo with an initial commit on main."""
    run_with_timeout(
        ["git", "init", "-b", "main"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    (repo_root / "README.md").write_text("# test repo\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "-A"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    run_with_timeout(
        ["git", "commit", "-m", "init"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _create_worktree(repo_root: Path, session_id: str, base_branch: str = "main") -> Path:
    """Create a worktree for the given session branch."""
    worktree_path = repo_root / "worktrees" / session_id
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    run_with_timeout(
        ["git", "worktree", "add", "-b", f"session/{session_id}", str(worktree_path), base_branch],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return worktree_path


@pytest.mark.requires_git
class TestGitOperations:
    def test_get_changed_files_current_branch(self, isolated_project_env: Path) -> None:
        repo_root = isolated_project_env / "repo-current"
        repo_root.mkdir()
        _init_git_repo(repo_root)

        # Create a feature branch and commit a change.
        run_with_timeout(
            ["git", "checkout", "-b", "feature/git-ops"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        src = repo_root / "src" / "api" / "routes" / "users.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# users endpoint\n", encoding="utf-8")
        run_with_timeout(
            ["git", "add", "-A"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        run_with_timeout(
            ["git", "commit", "-m", "add users endpoint"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

        from edison.core.utils import git as operations
        changed = operations.get_changed_files(repo_root, base_branch="main")
        rel_paths = {p.as_posix() for p in changed}

        assert "src/api/routes/users.py" in rel_paths

    def test_get_changed_files_for_session_worktree(self, isolated_project_env: Path) -> None:
        repo_root = isolated_project_env / "repo-worktree"
        repo_root.mkdir()
        _init_git_repo(repo_root)

        session_id = "session-123"
        worktree = _create_worktree(repo_root, session_id)

        # Commit a change in the session worktree branch.
        prisma_schema = worktree / "schema.prisma"
        prisma_schema.write_text("datasource db {}\n", encoding="utf-8")
        run_with_timeout(
            ["git", "add", "-A"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
        run_with_timeout(
            ["git", "commit", "-m", "add prisma schema"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )

        from edison.core.utils import git as operations
        changed = operations.get_changed_files(
            repo_root,
            base_branch="main",
            session_id=session_id,
        )
        rel_paths = {p.as_posix() for p in changed}

        assert "schema.prisma" in rel_paths

    def test_get_worktree_info_for_existing_session(self, isolated_project_env: Path) -> None:
        repo_root = isolated_project_env / "repo-worktree-info"
        repo_root.mkdir()
        _init_git_repo(repo_root)

        session_id = "session-456"
        worktree = _create_worktree(repo_root, session_id)

        from edison.core.utils import git as operations
        info = operations.get_worktree_info(session_id, repo_root)
        assert info is not None
        assert info.get("branch") in {f"session/{session_id}", session_id}
        assert Path(info["path"]).resolve() == worktree.resolve()

    def test_get_worktree_info_for_unknown_session(self, isolated_project_env: Path) -> None:
        repo_root = isolated_project_env / "repo-no-worktree"
        repo_root.mkdir()
        _init_git_repo(repo_root)

        from edison.core.utils import git as operations
        info = operations.get_worktree_info("does-not-exist", repo_root)
        assert info is None
