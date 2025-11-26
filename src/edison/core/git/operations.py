"""Thin git helpers used by Edison core."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.subprocess import run_git_command


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
                branch = ref[len("refs/heads/") :]
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

    Returns a small dictionary with at least ``path`` and ``branch`` keys, or
    ``None`` when no matching worktree is present.
    """
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
    """
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

