"""Pytest configuration and fixtures for E2E workflow tests.

Fixtures:
    - test_project_dir: Isolated .project directory for testing
    - test_git_repo: Isolated git repository with worktree support
    - repo_root: Path to actual repository root
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path

# Add tests directory to path so tests can import from helpers.*
TESTS_ROOT = Path(__file__).resolve().parent.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from helpers.env import TestProjectDir, TestGitRepo
from edison.core.utils.subprocess import run_with_timeout


@pytest.fixture
def repo_root() -> Path:
    """Get path to repository root.

    Returns:
        Path to repository root
    """
    # Robust detection: ascend until .git is found
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            # Skip the nested .edison git worktree; use project root instead.
            if current.name == ".edison" and (current.parent / ".git").exists():
                current = current.parent
                continue
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")


@pytest.fixture
def test_project_dir(tmp_path: Path, repo_root: Path) -> TestProjectDir:
    """Create isolated .project directory for testing.

    Args:
        tmp_path: pytest tmp_path fixture
        repo_root: Path to repository root

    Returns:
        TestProjectDir instance with isolated environment
    """
    return TestProjectDir(tmp_path, repo_root)


@pytest.fixture
def test_git_repo(tmp_path: Path) -> TestGitRepo:
    """Create isolated git repository for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        TestGitRepo instance with initialized git repository
    """
    return TestGitRepo(tmp_path)


@pytest.fixture
def combined_env(tmp_path: Path, repo_root: Path):
    """Combined fixture with both TestProjectDir and TestGitRepo.

    This fixture provides a unified testing environment with:
    - Initialized git repository
    - Isolated .project directory
    - Both classes configured to work together

    Args:
        tmp_path: pytest tmp_path fixture
        repo_root: Path to repository root

    Returns:
        Tuple of (TestProjectDir, TestGitRepo)
    """
    git_root = tmp_path / "git"
    proj_root = tmp_path / "proj"
    git_root.mkdir(parents=True, exist_ok=True)
    proj_root.mkdir(parents=True, exist_ok=True)

    git_repo = TestGitRepo(git_root)
    project_dir = TestProjectDir(proj_root, repo_root)
    return project_dir, git_repo


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "fast: marks tests as fast (select with '-m fast')"
    )
    config.addinivalue_line(
        "markers", "requires_git: marks tests that require git operations"
    )
    config.addinivalue_line(
        "markers", "requires_pnpm: marks tests that require pnpm/node"
    )
    config.addinivalue_line(
        "markers", "worktree: marks tests related to git worktree functionality"
    )
    config.addinivalue_line(
        "markers", "session: marks tests related to session management"
    )
    config.addinivalue_line(
        "markers", "task: marks tests related to task lifecycle"
    )
    config.addinivalue_line(
        "markers", "qa: marks tests related to QA/validation"
    )
    config.addinivalue_line(
        "markers", "context7: marks tests related to Context7 enforcement"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests (multiple components)"
    )
    config.addinivalue_line(
        "markers", "edge_case: marks edge case and error handling tests"
    )
    config.addinivalue_line(
        "markers", "security: marks security-critical tests (guard bypasses, isolation violations)"
    )


def _worktree_supported() -> bool:
    """Probe whether git worktree operations are supported in this environment."""
    import tempfile, subprocess
    from pathlib import Path
    try:
        tmp = Path(tempfile.mkdtemp(prefix="wt-probe-"))
        run_with_timeout(["git", "init", "-b", "main"], cwd=tmp, check=True, capture_output=True)
        run_with_timeout(["git", "config", "user.email", "probe@example.com"], cwd=tmp, check=True, capture_output=True)
        run_with_timeout(["git", "config", "user.name", "Probe"], cwd=tmp, check=True, capture_output=True)
        (tmp / "README.md").write_text("probe\n")
        run_with_timeout(["git", "add", "-A"], cwd=tmp, check=True, capture_output=True)
        run_with_timeout(["git", "commit", "-m", "init"], cwd=tmp, check=True, capture_output=True)
        wt = tmp / "_wt"
        r = run_with_timeout(["git", "worktree", "add", str(wt), "-b", "probe", "main"], cwd=tmp, capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    import pytest
    if not _worktree_supported():
        skip_marker = pytest.mark.skip(reason="git worktree not available in this environment")
        for item in items:
            if "requires_git" in item.keywords:
                item.add_marker(skip_marker)
