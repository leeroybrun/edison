"""Session git metadata helpers for worktree-managed sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..config_helpers import _config
from .create import resolve_worktree_target


def prepare_session_git_metadata(
    session_id: str,
    worktree_path: Optional[Path] = None,
    branch_name: Optional[str] = None,
    *,
    base_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare git metadata dict for session from worktree information."""
    cfg = _config().get_worktree_config()

    if worktree_path is None or branch_name is None:
        computed_path, computed_branch = resolve_worktree_target(session_id)
        worktree_path = worktree_path or computed_path
        branch_name = branch_name or computed_branch

    git_meta: Dict[str, Any] = {}

    if worktree_path:
        git_meta["worktreePath"] = str(worktree_path)
    if branch_name:
        git_meta["branchName"] = branch_name

    resolved_base = base_branch or cfg.get("baseBranch")
    if resolved_base is not None:
        git_meta["baseBranch"] = resolved_base

    return git_meta


__all__ = ["prepare_session_git_metadata"]

