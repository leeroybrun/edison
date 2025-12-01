"""Unit tests for session/current.py - worktree-aware session ID resolution.

This test suite uses REAL implementations instead of mocks:
- Real git repositories with actual git commands
- Real filesystem operations with temporary directories
- Real worktree creation and management
- Real session files and validation
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from edison.core.session.current import (
    get_current_session,
    set_current_session,
    clear_current_session,
    _is_in_worktree,
    _get_session_id_file,
    _read_session_id_file,
    _write_session_id_file,
    _delete_session_id_file,
    _SESSION_ID_FILENAME,
)
from edison.core.exceptions import SessionError
from edison.core.session.core.id import SessionIdError
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.env_setup import setup_project_root


def _init_git_repo(path: Path) -> None:
    """Initialize a real git repository."""
    run_with_timeout(
        ["git", "init", "-b", "main"],
        cwd=path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "config", "--local", "commit.gpgsign", "false"],
        cwd=path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout_type="git_operations",
    )
    # Create initial commit
    readme = path / "README.md"
    readme.write_text("# Test Repository\n")
    run_with_timeout(
        ["git", "add", "README.md"],
        cwd=path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout_type="git_operations",
    )


def _create_worktree(repo_path: Path, worktree_name: str) -> Path:
    """Create a real git worktree."""
    worktree_path = repo_path.parent / "worktrees" / worktree_name
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    branch_name = f"session/{worktree_name}"

    run_with_timeout(
        ["git", "worktree", "add", "-b", branch_name, str(worktree_path), "main"],
        cwd=repo_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout_type="git_operations",
    )

    return worktree_path


def _create_session_file(project_root: Path, session_id: str, state: str = "wip") -> Path:
    """Create a real session file."""
    import json
    from datetime import datetime, timezone

    sessions_dir = project_root / ".project" / "sessions" / state
    sessions_dir.mkdir(parents=True, exist_ok=True)

    session_file = sessions_dir / session_id / "session.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    session_data = {
        "meta": {
            "sessionId": session_id,
            "owner": "test-owner",
            "mode": "start",
            "status": state,
            "createdAt": now,
            "lastActive": now,
        },
        "state": state,
        "tasks": {},
        "qa": {},
        "git": {
            "worktreePath": None,
            "branchName": None,
            "baseBranch": None,
        },
        "activityLog": [
            {"timestamp": now, "message": "Session created"}
        ],
    }

    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(json.dumps(session_data, indent=2))
    return session_file


class TestIsInWorktree:
    """Tests for _is_in_worktree() helper."""

    def test_returns_true_when_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return True when in a real worktree."""
        # Create real git repo and worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Change to worktree directory
        monkeypatch.chdir(worktree_path)

        assert _is_in_worktree() is True

    def test_returns_false_when_not_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return False when in main git repository."""
        # Create real git repo but don't create worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        # Change to main repo directory
        monkeypatch.chdir(repo_path)

        assert _is_in_worktree() is False

    def test_returns_false_on_exception(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return False when not in a git repository at all."""
        # Create a directory that's not a git repo
        non_git_path = isolated_project_env / "not-a-repo"
        non_git_path.mkdir()

        monkeypatch.chdir(non_git_path)

        assert _is_in_worktree() is False


class TestGetSessionIdFile:
    """Tests for _get_session_id_file() helper."""

    def test_returns_path_when_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return file path when in worktree."""
        # Create real worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Worktree needs .project directory
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        # Set project root and change to worktree
        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        result = _get_session_id_file()
        assert result is not None
        assert result == project_dir / _SESSION_ID_FILENAME

    def test_returns_none_when_not_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return None when not in worktree."""
        # Create main repo but stay in it (not a worktree)
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        monkeypatch.chdir(repo_path)

        result = _get_session_id_file()
        assert result is None

    def test_returns_none_on_exception(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return None when PathResolver cannot resolve root."""
        # Create directory without git or .project
        non_project = isolated_project_env / "not-a-project"
        non_project.mkdir()

        # Clear project root env var so resolver fails
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        monkeypatch.chdir(non_project)

        result = _get_session_id_file()
        assert result is None


class TestReadSessionIdFile:
    """Tests for _read_session_id_file() helper."""

    def test_reads_valid_session_id(self, tmp_path: Path) -> None:
        """Should read and validate session ID from file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("test-session-123\n")

        result = _read_session_id_file(session_file)
        assert result == "test-session-123"

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Should return None for empty file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("")

        result = _read_session_id_file(session_file)
        assert result is None

    def test_returns_none_for_whitespace_only(self, tmp_path: Path) -> None:
        """Should return None for whitespace-only file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("   \n\t\n  ")

        result = _read_session_id_file(session_file)
        assert result is None

    def test_returns_none_on_read_error(self, tmp_path: Path) -> None:
        """Should return None when file cannot be read."""
        session_file = tmp_path / "nonexistent" / ".session-id"

        result = _read_session_id_file(session_file)
        assert result is None


class TestWriteSessionIdFile:
    """Tests for _write_session_id_file() helper."""

    def test_writes_session_id(self, tmp_path: Path) -> None:
        """Should write session ID to file."""
        session_file = tmp_path / ".project" / ".session-id"

        _write_session_id_file(session_file, "test-session-123")

        assert session_file.exists()
        assert session_file.read_text() == "test-session-123\n"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        session_file = tmp_path / "nested" / "dirs" / ".session-id"

        _write_session_id_file(session_file, "test-session-123")

        assert session_file.exists()
        assert session_file.parent.exists()

    def test_raises_session_error_on_write_failure(self, tmp_path: Path) -> None:
        """Should raise SessionError when write fails."""
        # Create a directory where file should be (causes write failure)
        session_file = tmp_path / ".session-id"
        session_file.mkdir()

        with pytest.raises(SessionError):
            _write_session_id_file(session_file, "test-session-123")


class TestDeleteSessionIdFile:
    """Tests for _delete_session_id_file() helper."""

    def test_deletes_existing_file(self, tmp_path: Path) -> None:
        """Should delete existing file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("test-session-123")

        _delete_session_id_file(session_file)

        assert not session_file.exists()

    def test_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Should not raise error for nonexistent file."""
        session_file = tmp_path / "nonexistent" / ".session-id"

        # Should not raise
        _delete_session_id_file(session_file)


class TestGetCurrentSession:
    """Tests for get_current_session() function."""

    def test_returns_stored_id_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return stored session ID when in worktree and file exists."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure in worktree
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        # Create session file to make session "exist"
        setup_project_root(monkeypatch, worktree_path)
        _create_session_file(worktree_path, "stored-session-123")

        # Write session ID file
        session_file = project_dir / ".session-id"
        session_file.write_text("stored-session-123\n")

        # Change to worktree
        monkeypatch.chdir(worktree_path)

        result = get_current_session()
        assert result == "stored-session-123"

    def test_falls_back_to_inference_when_stored_session_not_exists(
        self, isolated_project_env: Path, monkeypatch
    ) -> None:
        """Should fall back to inference when stored session no longer exists."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure in worktree
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        # Write session ID file for a session that doesn't exist
        session_file = project_dir / ".session-id"
        session_file.write_text("stale-session-123\n")

        # Create a different session that DOES exist for inference
        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.setenv("project_OWNER", "test-owner")
        _create_session_file(worktree_path, "inferred-session-456")

        # Change to worktree
        monkeypatch.chdir(worktree_path)

        result = get_current_session()
        # Should fall back to inference since stored session doesn't exist
        # In this case, inference won't find anything either (no owner-based lookup in current impl)
        # So result will be None
        assert result is None

    def test_falls_back_to_inference_when_no_file(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should fall back to inference when no session file exists."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure but no session ID file
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        result = get_current_session()
        # No session ID file, inference returns None
        assert result is None

    def test_uses_inference_when_not_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should use only inference when not in worktree."""
        # Create main git repo (not a worktree)
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        setup_project_root(monkeypatch, repo_path)
        monkeypatch.chdir(repo_path)

        result = get_current_session()
        # Not in worktree, no file storage, inference returns None
        assert result is None

    def test_returns_none_when_no_session_found(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should return None when no session can be determined."""
        # Create non-worktree environment with no sessions
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        setup_project_root(monkeypatch, repo_path)
        monkeypatch.chdir(repo_path)

        result = get_current_session()
        assert result is None


class TestSetCurrentSession:
    """Tests for set_current_session() function."""

    def test_writes_session_id_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should write session ID to file when in worktree."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure in worktree
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        set_current_session("new-session-123")

        session_file = project_dir / ".session-id"
        assert session_file.exists()
        assert "new-session-123" in session_file.read_text()

    def test_raises_error_when_not_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should raise SessionError when not in worktree."""
        # Create main git repo (not a worktree)
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        setup_project_root(monkeypatch, repo_path)
        monkeypatch.chdir(repo_path)

        with pytest.raises(SessionError) as exc_info:
            set_current_session("test-session-123")

        assert "worktree" in str(exc_info.value).lower()

    def test_validates_session_id_format(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should validate session ID format before writing."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure in worktree
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        # Try to set invalid session ID
        with pytest.raises(SessionIdError):
            set_current_session("invalid..id")


class TestClearCurrentSession:
    """Tests for clear_current_session() function."""

    def test_deletes_file_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should delete session file when in worktree."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure in worktree
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        # Create session ID file
        session_file = project_dir / ".session-id"
        session_file.write_text("test-session-123\n")

        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        clear_current_session()

        assert not session_file.exists()

    def test_noop_when_not_in_worktree(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should be a no-op when not in worktree."""
        # Create main git repo (not a worktree)
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        setup_project_root(monkeypatch, repo_path)
        monkeypatch.chdir(repo_path)

        # Should not raise
        clear_current_session()

    def test_handles_missing_file(self, isolated_project_env: Path, monkeypatch) -> None:
        """Should handle case when file doesn't exist."""
        # Create real git repo with worktree
        repo_path = isolated_project_env / "repo"
        repo_path.mkdir()
        _init_git_repo(repo_path)

        worktree_path = _create_worktree(repo_path, "test-session")

        # Create .project structure but no session ID file
        project_dir = worktree_path / ".project"
        project_dir.mkdir(parents=True)

        setup_project_root(monkeypatch, worktree_path)
        monkeypatch.chdir(worktree_path)

        # Should not raise
        clear_current_session()
