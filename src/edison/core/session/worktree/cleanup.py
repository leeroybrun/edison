"""Worktree cleanup and archival operations."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _get_repo_dir


def list_archived_worktrees_sorted() -> List[Path]:
    """List archived worktrees sorted by mtime (newest first)."""
    repo_dir = _get_repo_dir()
    cfg = _config().get_worktree_config()
    raw = cfg.get("archiveDirectory", ".worktrees/archive")
    raw_path = Path(raw)
    if raw_path.is_absolute():
        archive_dir = raw_path
    else:
        anchor = repo_dir if str(raw).startswith(".worktrees") else repo_dir.parent
        archive_dir = (anchor / raw).resolve()
    if not archive_dir.exists():
        return []
    dirs = [d for d in archive_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return dirs


def archive_worktree(session_id: str, worktree_path: Path, *, dry_run: bool = False) -> Path:
    """Move worktree to archive directory."""
    repo_dir = _get_repo_dir()
    config = _config().get_worktree_config()
    archive_dir_value = config.get("archiveDirectory", ".worktrees/archive")
    archive_root = Path(archive_dir_value)
    archive_full = archive_root if archive_root.is_absolute() else (repo_dir.parent / archive_dir_value).resolve()
    ensure_directory(archive_full)

    archived_path = archive_full / session_id

    if dry_run:
        return archived_path

    if worktree_path.exists():
        shutil.move(str(worktree_path), str(archived_path))

    try:
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(archived_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=10
        )
        run_with_timeout(
            ["git", "worktree", "prune"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass

    return archived_path


def cleanup_worktree(session_id: str, worktree_path: Path, branch_name: str, delete_branch: bool = False) -> None:
    """Remove worktree and optionally delete branch."""
    repo_dir = _get_repo_dir()
    try:
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(worktree_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass

    # Delete the branch if requested
    if delete_branch and branch_name:
        try:
            run_with_timeout(
                ["git", "branch", "-D", "--", branch_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                timeout=10
            )
        except Exception:
            pass


def remove_worktree(worktree_path: Path, branch_name: Optional[str] = None) -> None:
    """Best-effort removal of a worktree and optional branch cleanup."""
    repo_dir = _get_repo_dir()
    try:
        run_with_timeout(
            ["git", "worktree", "remove", "--force", "--", str(worktree_path)],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        try:
            if worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
        except Exception:
            pass

    if branch_name:
        try:
            run_with_timeout(
                ["git", "branch", "-D", "--", branch_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass


def prune_worktrees(*, dry_run: bool = False) -> None:
    """Prune stale git worktree references."""
    if dry_run:
        return
    repo_dir = _get_repo_dir()
    timeout = _config().get_worktree_timeout("health_check", 10)
    run_with_timeout(
        ["git", "worktree", "prune"],
        cwd=repo_dir,
        check=False,
        capture_output=True,
        timeout=timeout,
    )
