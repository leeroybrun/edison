"""Worktree management for Edison sessions.

This package provides worktree creation, management, and cleanup operations.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from edison.core.utils.subprocess import run_with_timeout

# Import low-level git operations from central utils
from edison.core.utils.git.worktree import (
    check_worktree_health,
    get_existing_worktree_path,
    is_worktree_registered,
    list_worktrees as _list_worktrees_raw,
)

# Import cleanup operations
from .cleanup import (
    list_archived_worktrees_sorted,
    archive_worktree,
    cleanup_worktree,
    remove_worktree,
    prune_worktrees,
)

# Import manager operations
from .manager import (
    resolve_worktree_target,
    create_worktree,
    restore_worktree,
    update_worktree_env,
    ensure_worktree_materialized,
    prepare_session_git_metadata,
    resolve_worktree_base_ref,
)

# Import config helpers
from .config_helpers import (
    _config,
    _get_worktree_base,
    _worktree_base_dir,
    _resolve_worktree_target,
)
from .._utils import get_repo_dir


def list_worktrees() -> List[Dict[str, Any]]:
    """List registered worktrees.
    
    Returns:
        List of dicts with 'path', 'head', 'branch', 'branch_ref' keys
    """
    return _list_worktrees_raw()


def list_worktrees_porcelain() -> str:
    """Return git worktree list output in porcelain format."""
    repo_dir = get_repo_dir()
    timeout = _config().get_worktree_timeout("health_check", 10)
    cp = run_with_timeout(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return cp.stdout


def worktree_health_check() -> Tuple[bool, List[str]]:
    """Check overall worktree configuration health."""
    ok = True
    notes: List[str] = []
    if shutil.which("git") is None:
        ok = False
        notes.append("git not found in PATH")
    try:
        cfg = _config().get_worktree_config()
        notes.append(f"baseDirectory: {cfg.get('baseDirectory')}")
        notes.append(f"archiveDirectory: {cfg.get('archiveDirectory', '.worktrees/archive')}")
        if not cfg.get("enabled", False):
            ok = False
            notes.append("worktrees.enabled=false")
    except Exception as e:
        ok = False
        notes.append(f"config error: {e}")
    return ok, notes


# Public API
__all__ = [
    # Manager functions
    "create_worktree",
    "restore_worktree",
    "resolve_worktree_target",
    "ensure_worktree_materialized",
    "update_worktree_env",
    "prepare_session_git_metadata",
    "resolve_worktree_base_ref",
    # Git operations
    "get_existing_worktree_path",
    "list_worktrees",
    "list_worktrees_porcelain",
    "is_worktree_registered",
    "worktree_health_check",
    "check_worktree_health",
    # Cleanup functions
    "archive_worktree",
    "cleanup_worktree",
    "remove_worktree",
    "prune_worktrees",
    "list_archived_worktrees_sorted",
    # Config helpers
    "_config",
    "_get_worktree_base",
    "_worktree_base_dir",
    "_resolve_worktree_target",
    # Utilities
    "get_repo_dir",
]
