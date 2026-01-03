"""Session worktree manager public API.

This module intentionally centralizes the public imports for the worktree
manager package so that `manager/__init__.py` stays tiny and stable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..cleanup import remove_worktree
from .create import (
    create_worktree,
    ensure_worktree_materialized,
    resolve_worktree_target,
    restore_worktree,
)
from .env import update_worktree_env
from .meta import (
    ensure_meta_worktree,
    get_meta_worktree_status,
    initialize_meta_shared_state,
    prepare_session_git_metadata,
    recreate_meta_shared_state,
)
from .post_install import _run_post_install_commands
from .refs import resolve_worktree_base_ref
from .session_id import (
    ensure_worktree_session_id_file,
    get_worktree_pinning_status,
    get_worktree_session_id_file_path,
)

__all__ = [
    "create_worktree",
    "restore_worktree",
    "resolve_worktree_target",
    "ensure_worktree_materialized",
    "ensure_worktree_session_id_file",
    "get_worktree_pinning_status",
    "get_worktree_session_id_file_path",
    "update_worktree_env",
    "_run_post_install_commands",
    "initialize_meta_shared_state",
    "recreate_meta_shared_state",
    "ensure_meta_worktree",
    "get_meta_worktree_status",
    "prepare_session_git_metadata",
    "resolve_worktree_base_ref",
    "WorktreeManager",
]


class WorktreeManager:
    """Back-compat OO wrapper around the functional worktree API."""

    def create_for_session(
        self,
        session_id: str,
        *,
        base_branch: Optional[str] = None,
        install_deps: Optional[bool] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        path, branch = create_worktree(
            session_id=str(session_id),
            base_branch=base_branch,
            install_deps=install_deps,
            dry_run=dry_run,
        )
        if not path or not branch:
            return {}
        return {"path": str(path), "branch": str(branch)}

    def remove_for_session(self, session_id: str, *, delete_branch: bool = False) -> None:
        path, branch = resolve_worktree_target(str(session_id))
        remove_worktree(path, branch if delete_branch else None)

