"""Session test fixtures.

Session-specific fixtures for state machine testing, worktree operations,
and recovery scenarios.

Most fixtures are consolidated in tests/conftest.py.
sys.path is already configured by tests/conftest.py.

Note: Session tests use session_git_repo_path fixture (returns Path, not TestGitRepo helper).

CRITICAL: All session tests MUST run in isolated environments to prevent
session persistence between tests causing failures.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def session_git_repo_path(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """Create isolated git repository for session tests.

    Session tests expect a Path object, not TestGitRepo helper.
    This fixture uses the TestGitRepo helper internally but returns the path.

    Sets up minimal .edison/config directory and environment for session configuration.

    Returns:
        Path to the git repository root.
    """
    from helpers.env import TestGitRepo
    from tests.helpers import reset_edison_caches, setup_project_root

    # Reset caches before setup
    reset_edison_caches()

    repo = TestGitRepo(tmp_path)

    # Create .edison/config directory for session tests
    config_dir = repo.repo_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set environment variables for isolation using centralized helper
    setup_project_root(monkeypatch, repo.repo_path)

    yield repo.repo_path

    # Cleanup caches after test
    reset_edison_caches()
