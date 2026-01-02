"""Resolve the filesystem root used for shared Edison state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from edison.core.utils.git.worktree import get_worktree_parent

from .meta_setup import ensure_meta_worktree_setup
from .meta_worktree import ensure_meta_worktree_checkout
from .shared_config import shared_state_cfg


def resolve_shared_root(*, repo_dir: Path, cfg: Dict[str, Any]) -> Path:
    ss = shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    if mode == "primary":
        return get_worktree_parent(repo_dir) or repo_dir

    if mode == "external":
        raw = ss.get("externalPath")
        if not raw:
            raise RuntimeError("worktrees.sharedState.mode=external requires worktrees.sharedState.externalPath")
        p = Path(str(raw))
        if not p.is_absolute():
            p = ((get_worktree_parent(repo_dir) or repo_dir) / p).resolve()
        return p

    # Default: meta
    meta_path, _branch, _created = ensure_meta_worktree_checkout(repo_dir=repo_dir, cfg=cfg, dry_run=False)
    ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)
    return meta_path


__all__ = ["resolve_shared_root"]

