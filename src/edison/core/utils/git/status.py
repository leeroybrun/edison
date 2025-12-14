"""High-level git status aggregation utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .diff import get_current_branch
from .worktree import get_worktree_info
from .repository import get_repo_root
from edison.core.utils.subprocess import run_git_command


def _resolve_cwd(repo_root: Path | str, session_id: Optional[str]) -> Path:
    root = Path(repo_root)
    if session_id:
        info = get_worktree_info(session_id, root)
        if info and "path" in info:
            return Path(info["path"])
    return root


def _parse_porcelain(lines: List[str]) -> Tuple[List[str], List[str], List[str]]:
    staged: List[str] = []
    modified: List[str] = []
    untracked: List[str] = []

    for raw in lines:
        line = raw.rstrip("\n")
        if not line:
            continue
        # Porcelain v1: XY <path> (rename/copy has ->)
        # Untracked lines begin with "?? "
        if line.startswith("?? "):
            path = line[3:]
            if path:
                untracked.append(path)
            continue

        if len(line) < 3:
            continue
        x = line[0]
        y = line[1]
        path = line[3:] if line[2] == " " else line[2:]
        if " -> " in path:
            path = path.split(" -> ", 1)[-1]

        # Index status (X) indicates staged changes
        if x not in (" ", "?"):
            staged.append(path)
        # Work tree status (Y) indicates unstaged modifications
        if y not in (" ", "?"):
            modified.append(path)

    return staged, modified, untracked


def get_status(
    repo_root: Path | str | None = None,
    *,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,  # reserved for future filtering
) -> Dict[str, Any]:
    """
    Return a git status summary:
    - branch: current branch name
    - clean: no staged/modified/untracked files
    - staged: list of staged file paths (relative to repo root)
    - modified: list of modified (unstaged) file paths
    - untracked: list of untracked file paths
    """
    repo = get_repo_root(repo_root) if repo_root is not None else get_repo_root()
    cwd = _resolve_cwd(repo, session_id)

    # Collect porcelain status
    result = run_git_command(
        # IMPORTANT: use file-level untracked paths (not collapsed directories like "apps/").
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.splitlines()
    staged, modified, untracked = _parse_porcelain(lines)

    branch = get_current_branch(cwd)
    clean = len(staged) == 0 and len(modified) == 0 and len(untracked) == 0

    return {
        "branch": branch,
        "clean": clean,
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
    }


__all__ = ["get_status"]

