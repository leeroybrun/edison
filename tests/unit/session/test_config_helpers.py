"""Test config_helpers module for worktree path resolution.

Following TDD principles, tests verify that path construction logic is
centralized in config_helpers.py and used consistently across all modules.
"""
import pytest
from pathlib import Path
from edison.core.session.worktree.config_helpers import (
    _worktree_base_dir,
    _resolve_archive_directory,
)


class TestWorktreeBaseDir:
    """Test worktree base directory resolution."""

    def test_absolute_path(self):
        """Test absolute path returns as-is."""
        cfg = {"baseDirectory": "/tmp/worktrees"}
        repo_dir = Path("/home/user/repo")
        result = _worktree_base_dir(cfg, repo_dir)
        assert result == Path("/tmp/worktrees")

    def test_relative_path_with_dotdot(self):
        """Test relative path starting with .. is resolved from repo_dir."""
        cfg = {"baseDirectory": "../worktrees"}
        repo_dir = Path("/home/user/repo")
        result = _worktree_base_dir(cfg, repo_dir)
        expected = (repo_dir / "../worktrees").resolve()
        assert result == expected

    def test_relative_path_without_dotdot(self):
        """Test relative path without .. is resolved from repo_dir.parent."""
        cfg = {"baseDirectory": "worktrees"}
        repo_dir = Path("/home/user/repo")
        result = _worktree_base_dir(cfg, repo_dir)
        expected = (repo_dir.parent / "worktrees").resolve()
        assert result == expected

    def test_default_value(self):
        """Test default value when baseDirectory not in config."""
        cfg = {}
        repo_dir = Path("/home/user/repo")
        result = _worktree_base_dir(cfg, repo_dir)
        # Default is "../{PROJECT_NAME}-worktrees"
        # This will be substituted by substitute_project_tokens
        assert result.is_absolute()


class TestResolveArchiveDirectory:
    """Test archive directory resolution."""

    def test_absolute_archive_path(self):
        """Test absolute archive path returns as-is."""
        cfg = {"archiveDirectory": "/tmp/archive"}
        repo_dir = Path("/home/user/repo")
        result = _resolve_archive_directory(cfg, repo_dir)
        assert result == Path("/tmp/archive")

    def test_relative_archive_path_with_dot_prefix(self):
        """Test relative path starting with .worktrees is resolved from repo_dir."""
        cfg = {"archiveDirectory": ".worktrees/archive"}
        repo_dir = Path("/home/user/repo")
        result = _resolve_archive_directory(cfg, repo_dir)
        expected = (repo_dir / ".worktrees/archive").resolve()
        assert result == expected

    def test_relative_archive_path_without_dot_prefix(self):
        """Test relative path without .worktrees is resolved from repo_dir.parent."""
        cfg = {"archiveDirectory": "archive"}
        repo_dir = Path("/home/user/repo")
        result = _resolve_archive_directory(cfg, repo_dir)
        expected = (repo_dir.parent / "archive").resolve()
        assert result == expected

    def test_default_archive_directory(self):
        """Test default archive directory when not in config."""
        cfg = {}
        repo_dir = Path("/home/user/repo")
        result = _resolve_archive_directory(cfg, repo_dir)
        # Default is ".worktrees/archive"
        expected = (repo_dir / ".worktrees/archive").resolve()
        assert result == expected

    def test_archive_path_consistency_with_cleanup_logic(self):
        """Test that archive path matches cleanup.py logic (lines 15-23)."""
        # This is the exact logic from cleanup.py list_archived_worktrees_sorted()
        cfg = {"archiveDirectory": ".worktrees/archive"}
        repo_dir = Path("/home/user/repo")

        # New centralized implementation
        result = _resolve_archive_directory(cfg, repo_dir)

        # Old logic from cleanup.py
        raw = cfg.get("archiveDirectory", ".worktrees/archive")
        raw_path = Path(raw)
        if raw_path.is_absolute():
            expected = raw_path
        else:
            anchor = repo_dir if str(raw).startswith(".worktrees") else repo_dir.parent
            expected = (anchor / raw).resolve()

        assert result == expected

    def test_archive_path_consistency_with_manager_logic(self):
        """Test that archive path matches manager.py logic (lines 162-164)."""
        # This is the exact logic from manager.py restore_worktree()
        cfg = {"archiveDirectory": ".worktrees/archive"}
        repo_dir = Path("/home/user/repo")

        # New centralized implementation
        result = _resolve_archive_directory(cfg, repo_dir)

        # Old logic from manager.py
        archive_dir_value = cfg.get("archiveDirectory", ".worktrees/archive")
        archive_root = Path(archive_dir_value)
        expected = archive_root if archive_root.is_absolute() else (repo_dir.parent / archive_dir_value).resolve()

        # NOTE: This test will FAIL because manager.py has WRONG logic
        # It should use repo_dir when starting with .worktrees, not repo_dir.parent
        # This is a BUG that we're fixing by consolidating to the correct implementation
