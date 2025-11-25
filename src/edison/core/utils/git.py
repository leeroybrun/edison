from __future__ import annotations

"""Lightweight git helpers shared by Edison scripts."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from ..paths import PathResolver, get_git_root
from .subprocess import run_with_timeout


def _starting_path(start_path: Optional[Path | str]) -> Path:
    if start_path is None:
        return Path.cwd().resolve()
    return Path(start_path).resolve()


def get_repo_root(start_path: Optional[Path | str] = None) -> Path:
    """Return the git repository root for ``start_path`` or current directory."""
    override = os.environ.get("AGENTS_PROJECT_ROOT")
    if override:
        path = Path(override).expanduser().resolve()
        if path.exists():
            return path
    start = _starting_path(start_path)
    try:
        result = run_with_timeout(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            check=True,
            timeout_type="git_operations",
        )
        root = Path(result.stdout.strip()).resolve()
        if root.exists():
            return root
    except Exception:
        pass

    resolved = get_git_root(start)
    if resolved is not None:
        return resolved
    return PathResolver.resolve_project_root()


def get_current_branch(start_path: Optional[Path | str] = None) -> str:
    """Return the current branch name."""
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
    """Return True when the working tree has no staged or unstaged changes."""
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


def _git_dir_info(start_path: Path) -> tuple[Path, Path]:
    """
    Return absolute git dir and common dir for the repository containing start_path.

    We intentionally run `git rev-parse` from the provided path (not the resolved
    repo root) so worktree detection honors the actual checkout we are inside.
    """
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
    """Return True when ``path`` is a linked worktree (not the primary checkout)."""
    try:
        start = _starting_path(path)
        if start.is_file():
            start = start.parent
        git_dir, common_dir = _git_dir_info(start)
    except Exception:
        return False
    return _is_worktree_dir(git_dir, common_dir)


def get_worktree_parent(path: Optional[Path | str] = None) -> Optional[Path]:
    """Return parent repository root when inside a worktree, otherwise None."""
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
