"""Worktree cleanup and archival operations."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _resolve_archive_directory
from .._utils import get_repo_dir

logger = logging.getLogger(__name__)


def list_archived_worktrees_sorted() -> List[Path]:
    """List archived worktrees sorted by mtime (newest first)."""
    repo_dir = get_repo_dir()
    cfg = _config().get_worktree_config()
    archive_dir = _resolve_archive_directory(cfg, repo_dir)
    if not archive_dir.exists():
        return []
    dirs = [d for d in archive_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs


def archive_worktree(session_id: str, worktree_path: Path, *, dry_run: bool = False) -> Path:
    """Move worktree to archive directory."""
    repo_dir = get_repo_dir()
    config = _config().get_worktree_config()
    archive_full = _resolve_archive_directory(config, repo_dir)
    ensure_directory(archive_full)

    archived_path = archive_full / session_id

    if dry_run:
        return archived_path

    if worktree_path.exists():
        shutil.move(str(worktree_path), str(archived_path))

    try:
        config = _config()
        timeout_health = config.get_worktree_timeout("health_check", 10)
        timeout_prune = config.get_worktree_timeout("prune", 10)
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(archived_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=timeout_health
        )
        run_with_timeout(
            ["git", "worktree", "prune"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=timeout_prune
        )
    except (OSError, RuntimeError, TimeoutError) as e:
        logger.warning("Failed to clean up worktree reference for %s: %s", session_id, e)

    return archived_path


def cleanup_worktree(session_id: str, worktree_path: Path, branch_name: str, delete_branch: bool = False) -> None:
    """Remove worktree and optionally delete branch."""
    repo_dir = get_repo_dir()
    config = _config()
    timeout = config.get_worktree_timeout("health_check", 10)
    try:
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(worktree_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=timeout
        )
    except (OSError, RuntimeError, TimeoutError) as e:
        logger.warning("Failed to remove worktree %s: %s", worktree_path, e)

    # Delete the branch if requested
    if delete_branch and branch_name:
        try:
            run_with_timeout(
                ["git", "branch", "-D", "--", branch_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                timeout=timeout
            )
        except (OSError, RuntimeError, TimeoutError) as e:
            logger.warning("Failed to delete branch %s: %s", branch_name, e)


def remove_worktree(worktree_path: Path, branch_name: Optional[str] = None) -> None:
    """Best-effort removal of a worktree and optional branch cleanup."""
    repo_dir = get_repo_dir()
    config = _config()
    timeout = config.get_worktree_timeout("health_check", 10)
    try:
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(worktree_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, RuntimeError, TimeoutError) as e:
        logger.warning("Failed to remove worktree %s, attempting manual cleanup: %s", worktree_path, e)
        try:
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
        except OSError as cleanup_err:
            logger.error("Manual worktree cleanup failed for %s: %s", worktree_path, cleanup_err)

    if branch_name:
        try:
            run_with_timeout(
                ["git", "branch", "-D", "--", branch_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                timeout=timeout,
            )
        except (OSError, RuntimeError, TimeoutError) as e:
            logger.warning("Failed to delete branch %s: %s", branch_name, e)


def prune_worktrees(*, dry_run: bool = False) -> None:
    """Prune stale git worktree references."""
    if dry_run:
        return
    repo_dir = get_repo_dir()
    timeout = _config().get_worktree_timeout("health_check", 10)
    run_with_timeout(
        ["git", "worktree", "prune"],
        cwd=repo_dir,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
