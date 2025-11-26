"""Worktree creation and management operations."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.file_io.utils import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _get_repo_dir, _resolve_worktree_target
from .git_ops import get_existing_worktree_for_branch


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

    existing_wt = get_existing_worktree_for_branch(branch_name)
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

            r = run_with_timeout(["git", "show-ref", "--verify", f"refs/heads/{branch_name}"], cwd=repo_dir, capture_output=True, text=True, timeout=5)
            if r.returncode != 0:
                run_with_timeout(["git", "checkout", base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_checkout)
                run_with_timeout(["git", "pull", "--ff-only"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_checkout)
                run_with_timeout(["git", "branch", branch_name, base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=5)

            run_with_timeout(["git", "worktree", "add", "--", str(worktree_path), branch_name], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_add)
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            run_with_timeout(["git", "worktree", "prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=10)
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)
            if attempt == 1:
                try:
                    ensure_directory(worktree_path.parent)
                    run_with_timeout(["git", "clone", "--local", "--no-hardlinks", "--", str(repo_dir), str(worktree_path)], check=True, capture_output=True, text=True, timeout=t_clone)
                    run_with_timeout(["git", "-C", str(worktree_path), "checkout", "-b", branch_name], check=True, capture_output=True, text=True, timeout=10)
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
                    run_with_timeout(["git", "-C", str(worktree_path), "checkout", "-b", branch_name], check=True, capture_output=True, text=True, timeout=10)
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Worktree pointer verification failed and clone fallback failed: {e.stderr or e}")
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    return (worktree_path, branch_name)


def restore_worktree(session_id: str, *, base_branch: Optional[str] = None, dry_run: bool = False) -> Path:
    """Restore a worktree from archive directory back to active worktrees."""
    repo_dir = _get_repo_dir()
    config_obj = _config()
    cfg = config_obj.get_worktree_config()

    worktree_path, branch_name = _resolve_worktree_target(session_id, cfg)
    archive_dir_value = cfg.get("archiveDirectory", ".worktrees/archive")
    archive_root = Path(archive_dir_value)
    archive_full = archive_root if archive_root.is_absolute() else (repo_dir.parent / archive_dir_value).resolve()
    src = archive_full / session_id
    if not src.exists():
        raise RuntimeError(f"Archived worktree not found: {src}")

    if dry_run:
        return worktree_path

    ensure_directory(worktree_path.parent)
    shutil.move(str(src), str(worktree_path))

    t_add = config_obj.get_worktree_timeout("worktree_add", 30)
    t_checkout = config_obj.get_worktree_timeout("checkout", 30)
    base_branch_value = base_branch or cfg.get("baseBranch", "main")

    r = run_with_timeout(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if r.returncode != 0:
        run_with_timeout(["git", "checkout", base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_checkout)
        run_with_timeout(["git", "branch", branch_name, base_branch_value], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=5)

    run_with_timeout(["git", "worktree", "add", "--", str(worktree_path), branch_name], cwd=repo_dir, check=True, capture_output=True, text=True, timeout=t_add)
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
