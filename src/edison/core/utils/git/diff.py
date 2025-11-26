"""Git diff and branch utilities."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .repository import get_repo_root
from .worktree import get_worktree_info


def get_current_branch(start_path: Optional[Path | str] = None) -> str:
    """Return the current branch name.

    Args:
        start_path: Starting path for resolution. Defaults to current directory.

    Returns:
        str: The current branch name.
    """
    from edison.core.utils.subprocess import run_with_timeout

    repo_root = get_repo_root(start_path)
    result = run_with_timeout(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    return (result.stdout or "").strip()


def is_clean_working_tree(start_path: Optional[Path | str] = None) -> bool:
    """Return True when the working tree has no staged or unstaged changes.

    Args:
        start_path: Starting path for resolution. Defaults to current directory.

    Returns:
        bool: True if the working tree is clean.
    """
    from edison.core.utils.subprocess import run_with_timeout

    repo_root = get_repo_root(start_path)
    result = run_with_timeout(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    return (result.stdout or "").strip() == ""


def get_changed_files(
    repo_root: Path,
    base_branch: str = "main",
    session_id: Optional[str] = None,
) -> List[Path]:
    """Get list of changed files for a session or the current branch.

    When ``session_id`` is provided, the diff is computed from the matching
    worktree (if found) against ``base_branch``. Otherwise the diff compares
    the current HEAD in ``repo_root`` with ``base_branch``.

    Paths are returned relative to the git working directory so callers can
    feed them directly into higher-level routing or rules engines.

    Args:
        repo_root: Repository root path.
        base_branch: Base branch to compare against (default: "main").
        session_id: Optional session ID to find worktree for.

    Returns:
        List[Path]: List of changed file paths relative to the repository.
    """
    from edison.core.utils.subprocess import run_git_command

    repo_root = Path(repo_root)

    if session_id:
        info = get_worktree_info(session_id, repo_root)
        cwd = Path(info["path"]) if info is not None else repo_root
    else:
        cwd = repo_root

    result = run_git_command(
        ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )

    files: List[Path] = []
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        files.append(Path(line))
    return files


__all__ = [
    "get_current_branch",
    "is_clean_working_tree",
    "get_changed_files",
]
