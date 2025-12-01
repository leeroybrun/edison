"""Path helper utilities for tests.

This module provides centralized path resolution functions to eliminate
duplication across test files. All test files should import from here
instead of defining their own get_repo_root() functions.
"""
from __future__ import annotations

from pathlib import Path


def get_repo_root() -> Path:
    """Get the outermost repository root by finding all .git directories.

    This implementation finds the OUTERMOST .git directory, which correctly
    handles nested git repositories (like .edison). This ensures we always
    get the true project root, not a nested repo.

    Returns:
        Path: Absolute path to the outermost repository root

    Raises:
        RuntimeError: If no repository root can be found
    """
    current = Path(__file__).resolve()
    last_git_root: Path | None = None

    # Walk up the directory tree and find ALL .git directories
    while current != current.parent:
        if (current / ".git").exists():
            last_git_root = current
        current = current.parent

    if last_git_root is None:
        raise RuntimeError("Could not find repository root")

    return last_git_root


def get_core_root() -> Path:
    """Get the Edison core root directory.

    Returns:
        Path: Absolute path to the .edison/core directory or bundled data path

    Raises:
        RuntimeError: If core root cannot be found
    """
    repo_root = get_repo_root()

    # First try .edison/core directory
    core_root = repo_root / ".edison" / "core"
    if core_root.exists():
        return core_root

    # Fallback to bundled edison.data path
    try:
        from edison.data import get_data_path
        return Path(get_data_path(""))
    except ImportError:
        pass

    raise RuntimeError(f"Could not find core directory at {core_root}")


