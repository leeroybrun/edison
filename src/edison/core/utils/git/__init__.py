"""Git utilities for Edison.

This package provides git-related utilities:
- Repository: detection and root resolution
- Worktree: worktree detection and management
- Diff: branch and diff operations
"""
from __future__ import annotations

from .diff import (
    get_changed_files,
    get_current_branch,
    is_clean_working_tree,
)
from .repository import (
    get_git_root,
    get_repo_root,
    is_git_repository,
)
from .worktree import (
    check_worktree_health,
    get_existing_worktree_path,
    get_worktree_info,
    get_worktree_parent,
    is_worktree,
    is_worktree_registered,
    list_worktrees,
)
from .status import get_status

__all__ = [
    # repository
    "is_git_repository",
    "get_git_root",
    "get_repo_root",
    # worktree
    "is_worktree",
    "get_worktree_parent",
    "get_worktree_info",
    "list_worktrees",
    "check_worktree_health",
    "get_existing_worktree_path",
    "is_worktree_registered",
    # diff
    "get_current_branch",
    "is_clean_working_tree",
    "get_changed_files",
    # status
    "get_status",
]



