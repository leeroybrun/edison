"""Meta shared-state initialization (link primary + configure existing worktrees)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.subprocess import run_with_timeout

from .._utils import get_repo_dir
from ..config_helpers import _config
from .meta_setup import ensure_checkout_git_excludes
from .meta_status import ensure_meta_worktree
from .shared_config import shared_state_cfg
from .shared_paths import ensure_shared_paths_in_checkout


def initialize_meta_shared_state(*, repo_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Initialize meta-shared state for primary + existing worktrees."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = ensure_meta_worktree(repo_dir=root, dry_run=dry_run)
    status["mode"] = mode
    if mode != "meta":
        return status

    primary_repo_dir = Path(status["primary_repo_dir"])
    meta_path = Path(status["meta_path"])

    if dry_run:
        status.update(
            {
                "primary_links_updated": 0,
                "shared_paths_primary_updated": 0,
                "shared_paths_primary_skipped_tracked": 0,
                "shared_paths_session_updated": 0,
                "shared_paths_session_skipped_tracked": 0,
                "session_worktrees_updated": 0,
                "primary_excludes_updated": False,
            }
        )
        return status

    primary_shared_updated, primary_shared_skipped_tracked = ensure_shared_paths_in_checkout(
        checkout_path=primary_repo_dir,
        repo_dir=primary_repo_dir,
        cfg=cfg,
        scope="primary",
    )
    ensure_checkout_git_excludes(checkout_path=primary_repo_dir, cfg=cfg, scope="primary")

    session_updated = 0
    session_shared_updated = 0
    session_shared_skipped_tracked = 0
    try:
        cp = run_with_timeout(
            ["git", "worktree", "list", "--porcelain"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=_config().get_worktree_timeout("health_check", 10),
        )
        current: Optional[Path] = None
        for line in (cp.stdout or "").splitlines():
            if line.startswith("worktree "):
                current = Path(line.split(" ", 1)[1].strip())
                continue
            if not line.strip():
                current = None
                continue
            if current is None:
                continue
            if line.startswith("HEAD "):
                p = current.resolve()
                if p == primary_repo_dir.resolve() or p == meta_path.resolve():
                    continue
                su, ss_tracked = ensure_shared_paths_in_checkout(
                    checkout_path=p,
                    repo_dir=p,
                    cfg=cfg,
                    scope="session",
                )
                session_shared_updated += su
                session_shared_skipped_tracked += ss_tracked
                ensure_checkout_git_excludes(checkout_path=p, cfg=cfg, scope="session")
                session_updated += 1
    except Exception:
        session_updated = 0

    status.update(
        {
            "primary_links_updated": int(primary_shared_updated),
            "shared_paths_primary_updated": int(primary_shared_updated),
            "shared_paths_primary_skipped_tracked": int(primary_shared_skipped_tracked),
            "shared_paths_session_updated": int(session_shared_updated),
            "shared_paths_session_skipped_tracked": int(session_shared_skipped_tracked),
            "session_worktrees_updated": int(session_updated),
            "primary_excludes_updated": True,
        }
    )
    return status


__all__ = ["initialize_meta_shared_state"]

