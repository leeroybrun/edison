"""Worktree management for Edison sessions."""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from ..paths.resolver import PathResolver
from .config import SessionConfig
from edison.core.utils.subprocess import run_with_timeout

# Shared session configuration instance used across worktree helpers.
_CONFIG = SessionConfig()


def _config() -> SessionConfig:
    """Return a fresh SessionConfig bound to the current project root."""
    return SessionConfig(repo_root=PathResolver.resolve_project_root())

def _get_repo_dir() -> Path:
    return PathResolver.resolve_project_root()

def _get_project_name() -> str:
    """Resolve the active project name."""
    # Use ConfigManager via SessionConfig if possible, or fallback to env
    # But SessionConfig loads full config, so we can check it there.
    # However, project name might be in 'project' key which SessionConfig doesn't expose directly yet?
    # Actually SessionConfig exposes full config via _full_config but it's private.
    # Let's stick to env var or simple config load if needed, but ideally ConfigManager handles it.
    name = os.environ.get("PROJECT_NAME")
    if not name:
        # Fallback to reading from defaults/config via ConfigManager
        # We can use _CONFIG._full_config if we make it public or add accessor
        # For now, let's assume ConfigManager handles it or we add accessor.
        # Let's add get_project_name to SessionConfig?
        # Or just rely on ConfigManager().load_config() here as before but cleaner.
        # The original code used ConfigManager().load_config(validate=False).
        # We can use _CONFIG._mgr.load_config() if we want to reuse the manager.
        pass
    return str(name or "project") # Fallback for now


def _resolve_worktree_target(session_id: str, cfg: Dict[str, Any]) -> tuple[Path, str]:
    """Compute worktree path and branch name from config and session id."""
    repo_dir = _get_repo_dir()

    base_dir_value = cfg.get("baseDirectory")
    if not base_dir_value:
        base_dir_value = f"../{os.environ.get('PROJECT_NAME', 'project')}-worktrees"

    base_dir_path = Path(base_dir_value)
    if base_dir_path.is_absolute():
        worktree_path = (base_dir_path / session_id).resolve()
    else:
        # Anchor relative paths to the *parent* of the repo so worktrees sit
        # alongside the repo instead of inside it.
        worktree_path = (repo_dir.parent / base_dir_value / session_id).resolve()

    branch_prefix = cfg.get("branchPrefix", "session/")
    branch_name = f"{branch_prefix}{session_id}"
    return worktree_path, branch_name


def resolve_worktree_target(session_id: str) -> tuple[Path, str]:
    """Public helper to compute target path/branch using current config."""
    cfg = _config().get_worktree_config()
    return _resolve_worktree_target(session_id, cfg)

def _get_worktree_base() -> Path:
    """Compute worktree base directory."""
    cfg = _config().get_worktree_config()
    # Fallback logic if config is missing (shouldn't happen with defaults.yaml)
    base = cfg.get("baseDirectory")
    if not base:
        # Fallback to sibling directory
        project = os.environ.get("PROJECT_NAME", "project")
        base = f"../{project}-worktrees"
    return Path(base).resolve()

def _git_is_healthy(path: Path) -> bool:
    try:
        timeout = _config().get_worktree_timeout("health_check", 10)
        r = run_with_timeout(
            ["git", "rev-parse", "--is-inside-work-tree"], 
            cwd=path, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        return path.exists() and r.returncode == 0 and (r.stdout or "").strip() == "true"
    except Exception:
        return False

def _git_list_worktrees() -> List[tuple[Path, str]]:
    """Return list of (worktree_path, branch_name) for REPO_DIR."""
    repo_dir = _get_repo_dir()
    items: List[tuple[Path, str]] = []
    try:
        timeout = _config().get_worktree_timeout("health_check", 10)
        cp = run_with_timeout(
            ["git", "worktree", "list", "--porcelain"], 
            cwd=repo_dir, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=timeout
        )
        cur_path: Optional[Path] = None
        cur_branch: str = ""
        for line in cp.stdout.splitlines():
            if line.startswith("worktree "):
                if cur_path is not None:
                    items.append((cur_path, cur_branch))
                cur_path = Path(line.split(" ", 1)[1].strip())
                cur_branch = ""
            elif line.startswith("branch "):
                ref = line.split(" ", 1)[1].strip()
                if ref.startswith("refs/heads/"):
                    cur_branch = ref.split("/", 2)[-1]
                else:
                    cur_branch = ref
        if cur_path is not None:
            items.append((cur_path, cur_branch))
    except Exception:
        pass
    return items

def get_existing_worktree_for_branch(branch_name: str) -> Optional[Path]:
    """Return existing worktree path for a branch if present and healthy."""
    items = _git_list_worktrees()
    for p, br in items:
        if br == branch_name and _git_is_healthy(p):
            return p
    
    for p, _ in items:
        try:
            cp = run_with_timeout(
                ["git", "branch", "--show-current"], 
                cwd=p, 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if cp.returncode == 0 and (cp.stdout or "").strip() == branch_name and _git_is_healthy(p):
                return p
        except Exception:
            continue
    return None

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
            local_root.mkdir(parents=True, exist_ok=True)
            candidate = local_root / session_id
            if candidate.exists() and any(candidate.iterdir()):
                candidate = local_root / f"{session_id}-{uuid.uuid4().hex[:6]}"
            worktree_path = candidate
    except Exception:
        pass

    base_dir_full = worktree_path.parent
    base_dir_full.mkdir(parents=True, exist_ok=True)

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
                    worktree_path.parent.mkdir(parents=True, exist_ok=True)
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
                    worktree_path.parent.mkdir(parents=True, exist_ok=True)
                    run_with_timeout(["git", "clone", "--local", "--no-hardlinks", "--", str(repo_dir), str(worktree_path)], check=True, capture_output=True, text=True, timeout=t_clone)
                    run_with_timeout(["git", "-C", str(worktree_path), "checkout", "-b", branch_name], check=True, capture_output=True, text=True, timeout=10)
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Worktree pointer verification failed and clone fallback failed: {e.stderr or e}")
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    return (worktree_path, branch_name)

def archive_worktree(session_id: str, worktree_path: Path, *, dry_run: bool = False) -> Path:
    """Move worktree to archive directory."""
    repo_dir = _get_repo_dir()
    config = _config().get_worktree_config()
    archive_dir_value = config.get("archiveDirectory", ".worktrees/archive")
    archive_root = Path(archive_dir_value)
    archive_full = archive_root if archive_root.is_absolute() else (repo_dir.parent / archive_dir_value).resolve()
    archive_full.mkdir(parents=True, exist_ok=True)

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


def list_worktrees() -> List[tuple[Path, str]]:
    """Public wrapper for listing registered worktrees (path, branch)."""
    return _git_list_worktrees()


def list_worktrees_porcelain() -> str:
    """Return git worktree list output in porcelain format."""
    repo_dir = _get_repo_dir()
    timeout = _config().get_worktree_timeout("health_check", 10)
    cp = run_with_timeout(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return cp.stdout


def is_registered_worktree(path: Path) -> bool:
    target = path.resolve()
    for p, _ in _git_list_worktrees():
        try:
            if p.resolve() == target:
                return True
        except Exception:
            continue
    return False


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

    worktree_path.parent.mkdir(parents=True, exist_ok=True)
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


def worktree_health_check() -> Tuple[bool, List[str]]:
    ok = True
    notes: List[str] = []
    if shutil.which("git") is None:
        ok = False
        notes.append("git not found in PATH")
    try:
        cfg = _config().get_worktree_config()
        notes.append(f"baseDirectory: {cfg.get('baseDirectory')}")
        notes.append(f"archiveDirectory: {cfg.get('archiveDirectory', '.worktrees/archive')}")
        if not cfg.get("enabled", False):
            ok = False
            notes.append("worktrees.enabled=false")
    except Exception as e:
        ok = False
        notes.append(f"config error: {e}")
    return ok, notes

    if delete_branch:
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
