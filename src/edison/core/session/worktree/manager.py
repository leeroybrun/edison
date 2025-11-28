"""Worktree creation and management operations."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _get_repo_dir, _resolve_worktree_target, _resolve_archive_directory
from edison.core.utils.git.worktree import get_existing_worktree_path


def resolve_worktree_target(session_id: str) -> tuple[Path, str]:
    """Public helper to compute target path/branch using current config."""
    cfg = _config().get_worktree_config()
    return _resolve_worktree_target(session_id, cfg)


def create_worktree(
    session_id: str,
    base_branch: Optional[str] = None,
    install_deps: Optional[bool] = None,
    dry_run: bool = False,
) -> tuple[Optional[Path], Optional[str]]:
    """Create git worktree for session.

    When ``dry_run`` is True, only compute the target path/branch and return
    without mutating git state.
    """
    repo_dir = _get_repo_dir()
    config_obj = _config()
    config = config_obj.get_worktree_config()
    if not config.get("enabled", False):
        return (None, None)

    worktree_path, branch_name = _resolve_worktree_target(session_id, config)
    base_branch_value = base_branch or config.get("baseBranch", "main")

    existing_wt = get_existing_worktree_path(branch_name)
    if existing_wt is not None:
        return (existing_wt.resolve(), branch_name)

    # Fail fast when repo has no commits (unborn HEAD) to avoid claiming metadata
    try:
        hc = run_with_timeout(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=config_obj.get_worktree_timeout("health_check", 10),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Repository has no commits; cannot create worktree") from exc

    if dry_run:
        return (worktree_path, branch_name)

    try:
        if worktree_path.exists() and any(worktree_path.iterdir()):
            local_root = (repo_dir / ".worktrees").resolve()
            ensure_directory(local_root)
            candidate = local_root / session_id
            if candidate.exists() and any(candidate.iterdir()):
                candidate = local_root / f"{session_id}-{uuid.uuid4().hex[:6]}"
            worktree_path = candidate
    except Exception:
        pass

    base_dir_full = worktree_path.parent
    ensure_directory(base_dir_full)

    last_err: Optional[Exception] = None

    # Timeouts
    t_fetch = config_obj.get_worktree_timeout("fetch", 60)
    t_checkout = config_obj.get_worktree_timeout("checkout", 30)
    t_add = config_obj.get_worktree_timeout("worktree_add", 30)
    t_clone = config_obj.get_worktree_timeout("clone", 60)
    t_install = config_obj.get_worktree_timeout("install", 300)
    t_health = config_obj.get_worktree_timeout("health_check", 10)

    for attempt in range(2):
        try:
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)

            r = run_with_timeout(["git", "show-ref", "--verify", f"refs/heads/{branch_name}"], cwd=repo_dir, capture_output=True, text=True, timeout=config_obj.get_worktree_timeout("branch_check", 10))
            if r.returncode != 0:
                run_with_timeout(["git", "checkout", base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_checkout)
                run_with_timeout(["git", "pull", "--ff-only"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_checkout)
                run_with_timeout(["git", "branch", branch_name, base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=config_obj.get_worktree_timeout("branch_check", 10))

            run_with_timeout(["git", "worktree", "add", "--", str(worktree_path), branch_name], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_add)
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            run_with_timeout(["git", "worktree", "prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=config_obj.get_worktree_timeout("prune", 10))
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)
            if attempt == 1:
                try:
                    ensure_directory(worktree_path.parent)
                    run_with_timeout(["git", "clone", "--local", "--no-hardlinks", "--", str(repo_dir), str(worktree_path)], check=True, capture_output=True, text=True, timeout=t_clone)
                    run_with_timeout(["git", "-C", str(worktree_path), "checkout", "-b", branch_name], check=True, capture_output=True, text=True, timeout=t_checkout)
                    last_err = None
                    break
                except Exception as ce:
                    last_err = ce
    if last_err is not None:
        raise RuntimeError(f"Failed to create worktree after retries: {last_err}")

    install_flag = config.get("installDeps", False) if install_deps is None else bool(install_deps)
    if install_flag:
        try:
            run_with_timeout(["pnpm", "install"], cwd=worktree_path, check=False, capture_output=True, text=True, timeout=t_install)
        except Exception:
            pass

    try:
        hc1 = run_with_timeout(["git", "rev-parse", "--is-inside-work-tree"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        hc2 = run_with_timeout(["git", "branch", "--show-current"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        if (hc1.stdout or "").strip() != "true" or (hc2.stdout or "").strip() != branch_name:
            raise RuntimeError("Worktree health check failed")

        git_file = worktree_path / ".git"
        if git_file.exists() and git_file.is_file():
            try:
                content = git_file.read_text(encoding="utf-8", errors="ignore")
                if "gitdir:" in content:
                    target = content.split("gitdir:", 1)[1].strip()
                    if not (worktree_path / target).exists():
                        raise FileNotFoundError(target)
            except Exception:
                try:
                    if worktree_path.exists():
                        shutil.rmtree(worktree_path, ignore_errors=True)
                    ensure_directory(worktree_path.parent)
                    run_with_timeout(["git", "clone", "--local", "--no-hardlinks", "--", str(repo_dir), str(worktree_path)], check=True, capture_output=True, text=True, timeout=t_clone)
                    run_with_timeout(["git", "-C", str(worktree_path), "checkout", "-b", branch_name], check=True, capture_output=True, text=True, timeout=t_checkout)
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Worktree pointer verification failed and clone fallback failed: {e.stderr or e}")
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    return (worktree_path, branch_name)


def restore_worktree(session_id: str, *, base_branch: Optional[str] = None, dry_run: bool = False) -> Path:
    """Restore a worktree from archive directory back to active worktrees.

    Note: Since archive_worktree removes the worktree from git's tracking,
    we need to delete the archived directory and re-create the worktree
    using create_worktree. This ensures proper git registration.
    """
    repo_dir = _get_repo_dir()
    config_obj = _config()
    cfg = config_obj.get_worktree_config()

    worktree_path, branch_name = _resolve_worktree_target(session_id, cfg)
    archive_full = _resolve_archive_directory(cfg, repo_dir)
    src = archive_full / session_id
    if not src.exists():
        raise RuntimeError(f"Archived worktree not found: {src}")

    if dry_run:
        return worktree_path

    # Remove the archived directory - we'll recreate the worktree fresh
    # This is necessary because archive_worktree calls git worktree remove,
    # which destroys the git metadata in the parent repo
    shutil.rmtree(src, ignore_errors=True)

    # Re-create the worktree using the standard creation flow
    # This ensures it's properly registered with git
    created_path, created_branch = create_worktree(
        session_id=session_id,
        base_branch=base_branch,
        dry_run=False
    )

    if created_path != worktree_path:
        raise RuntimeError(f"Restored worktree path mismatch: expected {worktree_path}, got {created_path}")

    return worktree_path


def update_worktree_env(worktree_path: Path, database_url: str) -> None:
    """Update .env file in worktree with session database URL."""
    env_path = worktree_path / ".env"
    if env_path.exists():
        env_content = env_path.read_text()
    else:
        example_path = worktree_path / ".env.example"
        env_content = example_path.read_text() if example_path.exists() else ""

    import re as _re
    if _re.search(r"^DATABASE_URL=", env_content, _re.MULTILINE):
        env_content = _re.sub(r"^DATABASE_URL=.*$", f"DATABASE_URL=\"{database_url}\"", env_content, flags=_re.MULTILINE)
    else:
        env_content += f"\nDATABASE_URL=\"{database_url}\"\n"
    env_path.write_text(env_content)


def ensure_worktree_materialized(session_id: str) -> Dict[str, Any]:
    """Ensure worktree exists for session and return git metadata."""
    # This reconstructs the git metadata expected by the session
    path, branch = create_worktree(session_id)
    if path and branch:
        return {
            "worktreePath": str(path),
            "branchName": branch,
            # baseBranch is not returned by create_worktree, but we can infer or it's in session
            # For this return value, we just provide what we know.
            # The caller might merge this with existing session git meta.
        }
    return {}


def prepare_session_git_metadata(
    session_id: str,
    worktree_path: Optional[Path] = None,
    branch_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare git metadata dict for session from worktree information.

    This centralizes git metadata construction to avoid duplication across
    manager.py and autostart.py.

    Args:
        session_id: Session identifier
        worktree_path: Path to worktree (if None, will be computed)
        branch_name: Branch name (if None, will be computed)

    Returns:
        Dict with worktreePath, branchName, and baseBranch from config
    """
    cfg = _config().get_worktree_config()

    # Compute path and branch if not provided
    if worktree_path is None or branch_name is None:
        computed_path, computed_branch = resolve_worktree_target(session_id)
        worktree_path = worktree_path or computed_path
        branch_name = branch_name or computed_branch

    git_meta: Dict[str, Any] = {}

    if worktree_path:
        git_meta["worktreePath"] = str(worktree_path)

    if branch_name:
        git_meta["branchName"] = branch_name

    # Always include baseBranch from config
    base_branch = cfg.get("baseBranch", "main")
    git_meta["baseBranch"] = base_branch

    return git_meta
