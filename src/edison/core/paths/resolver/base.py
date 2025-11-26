"""Base definitions for path resolution."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


class EdisonPathError(ValueError):
    """Raised when path resolution fails.

    This includes:
    - Cannot resolve project root
    - Project root resolves to .edison directory (invalid)
    - Evidence directory not found
    - Invalid session ID format
    """
    pass


def is_git_repository(path: Path) -> bool:
    """Return True if ``path`` is inside a git repository.

    Walks up parent directories looking for a ``.git`` entry (file or
    directory). This is a lightweight structural check and does not run
    git commands, making it safe to call in non-git sandboxes.

    Args:
        path: Filesystem path to probe.

    Returns:
        bool: True if a ``.git`` entry is found, otherwise False.
    """
    p = Path(path).resolve()
    # If a file is passed, start from its parent directory
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return True
    return False


def get_git_root(path: Path) -> Optional[Path]:
    """Return the git repository root for ``path``, or None if not in a repo.

    This mirrors :func:`is_git_repository` by walking parents looking for a
    ``.git`` entry, but returns the first directory that contains it.

    Args:
        path: Filesystem path to probe.

    Returns:
        Optional[Path]: Git repository root directory, or None when no
        repository is detected.
    """
    p = Path(path).resolve()
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None
