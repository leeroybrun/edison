"""Git worktree detection and management utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .repository import get_repo_root


def _starting_path(start_path: Optional[Path | str]) -> Path:
    """Normalize start_path to an absolute Path."""
    if start_path is None:
        return Path.cwd().resolve()
    return Path(start_path).resolve()


def _git_dir_info(start_path: Path) -> tuple[Path, Path]:
    """Return absolute git dir and common dir for the repository containing start_path.

    We intentionally run `git rev-parse` from the provided path (not the resolved
    repo root) so worktree detection honors the actual checkout we are inside.
    """
    from edison.core.utils.subprocess import run_with_timeout

    git_dir = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-dir"],
        cwd=start_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    common_dir = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=start_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    return Path(git_dir.stdout.strip()), Path(common_dir.stdout.strip())


def _is_worktree_dir(git_dir: Path, common_dir: Path) -> bool:
    """Return True when git_dir points to a linked worktree directory."""
    if git_dir == common_dir:
        return False
    try:
        return git_dir.is_relative_to(common_dir / "worktrees")
    except AttributeError:
        return str(git_dir).startswith(str(common_dir / "worktrees"))


def is_worktree(path: Optional[Path | str] = None) -> bool:
    """Return True when ``path`` is a linked worktree (not the primary checkout).

    Args:
        path: Path to check. Defaults to current directory.

    Returns:
        bool: True if path is a linked worktree.
    """
    try:
        start = _starting_path(path)
        if start.is_file():
            start = start.parent
        git_dir, common_dir = _git_dir_info(start)
    except Exception:
        return False
    return _is_worktree_dir(git_dir, common_dir)


def get_worktree_parent(path: Optional[Path | str] = None) -> Optional[Path]:
    """Return parent repository root when inside a worktree, otherwise None.

    Args:
        path: Path to check. Defaults to current directory.

    Returns:
        Optional[Path]: Parent repository root, or None if not a worktree.
    """
    try:
        start = _starting_path(path)
        if start.is_file():
            start = start.parent
        git_dir, common_dir = _git_dir_info(start)
    except Exception:
        return None
    if not _is_worktree_dir(git_dir, common_dir):
        return None
    # Common dir is <parent>/.git
    return common_dir.parent.resolve()


def _parse_worktree_list(stdout: str) -> List[Dict[str, Any]]:
    """Parse ``git worktree list --porcelain`` output into a structured list."""
    worktrees: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}

    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue

        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
                current = {}
            path_str = line.split(" ", 1)[1]
            current["path"] = path_str
            continue

        if line.startswith("HEAD "):
            current["head"] = line.split(" ", 1)[1]
            continue

        if line.startswith("branch "):
            ref = line.split(" ", 1)[1]
            branch = ref
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/"):]
            current["branch_ref"] = ref
            current["branch"] = branch
            continue

    if current:
        worktrees.append(current)

    return worktrees


def get_worktree_info(session_id: str, repo_root: Path) -> Optional[Dict[str, Any]]:
    """Get worktree info for ``session_id`` if it exists.

    The lookup is tolerant and will match either:
    - a branch named ``session/<session_id>`` or exactly ``<session_id>``, or
    - a worktree directory whose name matches ``session_id``.

    Args:
        session_id: Session ID to look for.
        repo_root: Repository root path.

    Returns:
        A dictionary with ``path``, ``branch``, and ``head`` keys, or None.
    """
    from edison.core.utils.subprocess import run_git_command

    repo_root = Path(repo_root)

    result = run_git_command(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    entries = _parse_worktree_list(result.stdout)

    for entry in entries:
        path_str = entry.get("path")
        if not path_str:
            continue

        branch = entry.get("branch") or ""
        path = Path(path_str)

        if branch in {f"session/{session_id}", session_id}:
            return {
                "path": str(path),
                "branch": branch,
                "head": entry.get("head"),
            }

        if path.name == session_id or path.as_posix().endswith(f"/{session_id}"):
            return {
                "path": str(path),
                "branch": branch or None,
                "head": entry.get("head"),
            }

    return None


__all__ = [
    "is_worktree",
    "get_worktree_parent",
    "get_worktree_info",
    "_parse_worktree_list",
    "_git_dir_info",
    "_is_worktree_dir",
]
