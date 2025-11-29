"""Pytest configuration for E2E workflow tests.

Fixtures (repo_root, project_dir, git_repo, combined_env) are now
consolidated in tests/conftest.py to avoid duplication.

This file only contains E2E-specific marker configuration and collection hooks.
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout


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
