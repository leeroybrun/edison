"""Meta worktree status + ensure helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.git.worktree import get_worktree_parent, is_worktree_registered

from .._utils import get_repo_dir
from ..config_helpers import _config
from .meta_setup import ensure_meta_worktree_setup
from .meta_worktree import ensure_meta_worktree_checkout, resolve_meta_worktree_path
from .shared_config import shared_state_cfg


def get_meta_worktree_status(*, repo_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Return computed status for the shared-state meta worktree without creating it."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    primary_repo_dir = get_worktree_parent(root) or root
    meta_path = resolve_meta_worktree_path(cfg=cfg, repo_dir=primary_repo_dir)
    branch = str(ss.get("metaBranch") or "edison-meta")

    exists = meta_path.exists()
    registered = False
    if exists:
        try:
            registered = is_worktree_registered(meta_path, repo_root=primary_repo_dir)
        except Exception:
            registered = False

    return {
        "mode": mode,
        "primary_repo_dir": str(primary_repo_dir),
        "meta_path": str(meta_path),
        "meta_branch": branch,
        "exists": exists,
        "registered": registered,
    }


def ensure_meta_worktree(*, repo_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Ensure the shared-state meta worktree exists (when mode=meta) and return status."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = get_meta_worktree_status(repo_dir=root)
    if mode != "meta":
        status["created"] = False
        return status

    meta_path, branch, created = ensure_meta_worktree_checkout(repo_dir=root, cfg=cfg, dry_run=dry_run)
    if not dry_run:
        ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)
    status.update(
        {
            "meta_path": str(meta_path),
            "meta_branch": str(branch),
            "created": bool(created),
            "exists": meta_path.exists(),
            "registered": is_worktree_registered(meta_path, repo_root=get_worktree_parent(root) or root)
            if meta_path.exists()
            else False,
        }
    )
    return status


__all__ = ["ensure_meta_worktree", "get_meta_worktree_status"]

