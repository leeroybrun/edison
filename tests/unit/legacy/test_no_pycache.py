"""Test that __pycache__ directories are not committed to git.

This test verifies that __pycache__ directories are properly gitignored,
NOT that they don't exist locally (they're expected to exist during development).
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_pycache_directories_tracked_in_git():
    """__pycache__ directories should not be tracked in git."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "**/__pycache__/*"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    tracked_pycache = [f for f in result.stdout.strip().split("\n") if f]
    assert not tracked_pycache, f"__pycache__ files tracked in git: {tracked_pycache}"
