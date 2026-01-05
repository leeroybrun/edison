"""Path helper utilities for tests.

This module provides centralized path resolution functions to eliminate
duplication across test files. All test files should import from here
instead of defining their own get_repo_root() functions.
"""
from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root for the current checkout.

    This implementation finds the CLOSEST parent directory containing a `.git`
    entry (directory or worktree pointer file). This ensures E2E subprocesses
    run against the same checkout under test, even when the checkout is a git
    worktree nested under another repository directory (common in Edison
    multi-worktree workflows).

    Returns:
        Path: Absolute path to the repository root

    Raises:
        RuntimeError: If no repository root can be found
    """
    current = Path(__file__).resolve()

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    raise RuntimeError("Could not find repository root")


def get_core_root() -> Path:
    """Get the Edison core root directory (bundled data).
    
    Core content is ALWAYS from the bundled edison.data package.
    NO .edison/core/ support - that is legacy.

    Returns:
        Path: Absolute path to the bundled edison.data directory

    Raises:
        RuntimeError: If bundled data cannot be found
    """
    from edison.data import get_data_path
    return Path(get_data_path(""))

