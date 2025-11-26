"""Worktree management for Edison sessions.

This package provides worktree creation, management, and cleanup operations.
"""
from __future__ import annotations

# Import git operations
from .git_ops import (
    get_existing_worktree_for_branch,
    list_worktrees,
    list_worktrees_porcelain,
    is_registered_worktree,
    worktree_health_check,
    # Internal functions (exported for testing)
    _git_is_healthy,
    _git_list_worktrees,
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
)

# Import config helpers
from .config_helpers import (
    _config,
    _get_repo_dir,
    _get_worktree_base,
    _worktree_base_dir,
    _resolve_worktree_target,
)

# Public API
__all__ = [
    # Manager functions
    "create_worktree",
    "restore_worktree",
    "resolve_worktree_target",
    "ensure_worktree_materialized",
    "update_worktree_env",
    # Git operations
    "get_existing_worktree_for_branch",
    "list_worktrees",
    "list_worktrees_porcelain",
    "is_registered_worktree",
    "worktree_health_check",
    # Cleanup functions
    "archive_worktree",
    "cleanup_worktree",
    "remove_worktree",
    "prune_worktrees",
    "list_archived_worktrees_sorted",
    # Internal helpers (for testing)
    "_config",
    "_get_repo_dir",
    "_get_worktree_base",
    "_worktree_base_dir",
    "_resolve_worktree_target",
    "_git_is_healthy",
    "_git_list_worktrees",
]
