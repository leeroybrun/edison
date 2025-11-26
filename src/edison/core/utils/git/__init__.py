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
    get_worktree_info,
    get_worktree_parent,
    is_worktree,
)

__all__ = [
    # repository
    "is_git_repository",
    "get_git_root",
    "get_repo_root",
    # worktree
    "is_worktree",
    "get_worktree_parent",
    "get_worktree_info",
    # diff
    "get_current_branch",
    "is_clean_working_tree",
    "get_changed_files",
]
