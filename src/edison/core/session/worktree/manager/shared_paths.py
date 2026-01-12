"""Shared-path symlink and tracking helpers for worktree management."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

from edison.core.utils.git.worktree import get_worktree_parent
from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout

from ..config_helpers import _config
from .shared_config import parse_shared_paths
from .shared_root import resolve_shared_root


def _path_is_tracked(*, checkout_path: Path, rel_path: str) -> bool:
    """Return True if `rel_path` is tracked in the checkout's index."""
    try:
        cp = run_with_timeout(
            ["git", "ls-files", "-z", "--", rel_path],
            cwd=checkout_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )
        return bool((cp.stdout or "").strip())
    except Exception:
        return False


def _ensure_symlink_with_merge(
    *,
    link: Path,
    target: Path,
    item_type: str,
    merge_existing: bool,
) -> bool:
    """Ensure `link` is a symlink to `target`, optionally merging existing content."""
    try:
        if item_type == "dir":
            ensure_directory(target)
        else:
            ensure_directory(target.parent)

        if link.is_symlink():
            try:
                if link.resolve() == target.resolve():
                    return False
            except Exception:
                pass
            try:
                link.unlink()
            except Exception:
                return False

        if link.exists() and not link.is_symlink():
            if item_type == "dir" and link.is_dir():
                if merge_existing:
                    try:
                        for child in link.iterdir():
                            dest = target / child.name
                            if dest.exists():
                                continue
                            shutil.move(str(child), str(dest))
                    except Exception:
                        return False
                try:
                    shutil.rmtree(link, ignore_errors=True)
                except Exception:
                    return False
            elif item_type == "file" and link.is_file():
                if merge_existing and not target.exists():
                    try:
                        shutil.move(str(link), str(target))
                    except Exception:
                        return False
                else:
                    return False
            else:
                return False

        if not link.exists():
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(target, target_is_directory=(item_type == "dir"))
            except Exception:
                if item_type == "dir":
                    ensure_directory(link)
                return False
            return True
    except Exception:
        return False
    return False


def ensure_shared_paths_in_checkout(
    *,
    checkout_path: Path,
    repo_dir: Path,
    cfg: Dict[str, Any],
    scope: str,
) -> Tuple[int, int]:
    """Ensure configured shared paths exist as symlinks in the checkout.

    Returns (updated_count, skipped_tracked_count).
    """
    updated = 0
    skipped_tracked = 0

    shared_root_cache: Path | None = None
    primary_root_cache: Path | None = None

    for item in parse_shared_paths(cfg):
        scopes = set(item.get("scopes") or [])
        if scope not in scopes:
            continue

        raw = str(item.get("path") or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_absolute() or ".." in p.parts:
            continue
        rel = str(p)

        if _path_is_tracked(checkout_path=checkout_path, rel_path=rel):
            skipped_tracked += 1
            continue

        item_type = str(item.get("type") or "dir").strip().lower()
        merge_existing = bool(item.get("mergeExisting", True))
        only_if_target_exists = bool(item.get("onlyIfTargetExists", False))
        target_root = str(item.get("targetRoot") or "shared").strip().lower()
        if target_root == "primary":
            if primary_root_cache is None:
                primary_root_cache = get_worktree_parent(repo_dir) or repo_dir
            shared_root = primary_root_cache
        else:
            if shared_root_cache is None:
                shared_root_cache = resolve_shared_root(repo_dir=repo_dir, cfg=cfg)
            shared_root = shared_root_cache

        link = checkout_path / rel
        target = Path(shared_root) / rel
        if only_if_target_exists and not target.exists():
            continue
        if _ensure_symlink_with_merge(
            link=link,
            target=target,
            item_type=item_type,
            merge_existing=merge_existing,
        ):
            updated += 1

    return updated, skipped_tracked


__all__ = ["ensure_shared_paths_in_checkout"]
