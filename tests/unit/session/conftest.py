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
import shutil
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def session_git_repo_template(tmp_path_factory) -> Path:
    """Create a reusable git repo template (built once per test session).

    Worktree-heavy tests are expensive when each test runs `git init` + initial
    commits. Instead, we build a single template repo and copy it per test to
    keep isolation while speeding up setup.
    """
    from helpers.env import TestGitRepo

    base = tmp_path_factory.mktemp("session-git-template")
    repo = TestGitRepo(base)
    return repo.repo_path


@pytest.fixture
def session_git_repo_path(
    tmp_path: Path, monkeypatch, session_git_repo_template: Path
) -> Generator[Path, None, None]:
    """Create isolated git repository for session tests.

    Session tests expect a Path object, not TestGitRepo helper.
    This fixture uses the TestGitRepo helper internally but returns the path.

    Sets up minimal .edison/config directory and environment for session configuration.

    Returns:
        Path to the git repository root.
    """
    from tests.helpers import reset_edison_caches, setup_project_root

    # Reset caches before setup
    reset_edison_caches()

    # Copy template repo into the per-test tmp_path (keeps isolation, avoids re-initting git).
    shutil.copytree(session_git_repo_template, tmp_path, dirs_exist_ok=True)
    repo_path = tmp_path

    # Create .edison/config directory for session tests
    config_dir = repo_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Set environment variables for isolation using centralized helper
    setup_project_root(monkeypatch, repo_path)

    yield repo_path

    # Cleanup caches after test
    reset_edison_caches()
