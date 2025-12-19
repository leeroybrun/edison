"""Worktree creation and management operations."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _resolve_worktree_target, _resolve_archive_directory
from .._utils import get_repo_dir
from edison.core.utils.git.worktree import get_existing_worktree_path
import re as _re


def _ensure_shared_sessions_dir(*, worktree_path: Path, repo_dir: Path) -> None:
    """Ensure `<project-management-dir>/sessions` is shared across git worktrees.

    Git worktrees do not share untracked files. Edison stores session runtime state
    under `<project-management-dir>/sessions`, so we create a symlink in the worktree that points
    to the primary checkout's sessions directory.
    """
    try:
        from edison.core.utils.paths import get_management_paths

        mgmt_dir_name = get_management_paths(repo_dir).get_management_root().name
        shared = (repo_dir / mgmt_dir_name / "sessions").resolve()
        ensure_directory(shared)

        project_dir = worktree_path / mgmt_dir_name
        ensure_directory(project_dir)

        link = project_dir / "sessions"

        if link.is_symlink():
            try:
                if link.resolve() == shared:
                    return
            except Exception:
                pass

        if link.exists() and link.is_dir() and not link.is_symlink():
            # Best-effort merge: move any existing entries into the shared dir.
            try:
                for child in link.iterdir():
                    dest = shared / child.name
                    if dest.exists():
                        continue
                    shutil.move(str(child), str(dest))
            except Exception:
                # If merge fails, do not risk data loss; keep existing directory.
                return
            try:
                shutil.rmtree(link, ignore_errors=True)
            except Exception:
                return

        if link.exists() and not link.is_symlink():
            # Unexpected file type; avoid clobbering.
            return

        if not link.exists():
            try:
                link.symlink_to(shared, target_is_directory=True)
            except Exception:
                # Fallback: create a local directory (sessions won't be shared).
                ensure_directory(link)
    except Exception:
        # Never block worktree creation on best-effort linking.
        return


def _ensure_worktree_session_id_file(*, worktree_path: Path, session_id: str) -> None:
    """Ensure `<project-management-dir>/.session-id` exists inside the worktree.

    This enables worktree-local session auto-resolution (e.g. `edison session status`
    without passing `--session` or setting env vars) by allowing the canonical resolver
    to read the session id from the worktree's management root.
    """
    try:
        from edison.core.utils.paths import PathResolver, get_management_paths

        repo_root = PathResolver.resolve_project_root()
        mgmt_dir_name = get_management_paths(repo_root).get_management_root().name
        project_dir = worktree_path / mgmt_dir_name
        ensure_directory(project_dir)
        target = project_dir / ".session-id"
        try:
            if target.exists() and target.read_text(encoding="utf-8").strip() == session_id:
                return
        except Exception:
            pass
        target.write_text(session_id + "\n", encoding="utf-8")
    except Exception:
        # Never block worktree creation on best-effort session id persistence.
        return


def _primary_head_marker(repo_dir: Path) -> str:
    """Return a stable marker for the primary worktree HEAD.

    Worktree operations must never switch the branch (or detached HEAD) of the
    primary worktree. This marker is used to assert that invariant.
    """
    timeout = _config().get_worktree_timeout("branch_check", 10)
    try:
        cp = run_with_timeout(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        ref = (cp.stdout or "").strip()
        if ref and ref != "HEAD":
            return ref
    except Exception:
        pass
    try:
        cp2 = run_with_timeout(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        sha = (cp2.stdout or "").strip()
        return f"DETACHED@{sha}" if sha else "DETACHED"
    except Exception:
        return "UNKNOWN"


def _resolve_current_base_ref(repo_dir: Path) -> str:
    """Resolve the base ref for baseBranchMode=current without mutating git state."""
    marker = _primary_head_marker(repo_dir)
    if marker.startswith("DETACHED@"):
        return marker.split("@", 1)[1]
    if marker in {"UNKNOWN", "DETACHED"}:
        return "HEAD"
    return marker


def _resolve_start_ref(repo_dir: Path, base_ref: str, *, timeout: int) -> str:
    """Resolve a start ref that can be passed to `git worktree add`.

    Accepts branch names, remote branches, SHAs, and HEAD.
    """

    def _rev_parse_ok(ref: str) -> bool:
        rr = run_with_timeout(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return rr.returncode == 0

    if _rev_parse_ok(base_ref):
        return base_ref

    # Try origin/<ref> without requiring a local checkout.
    if base_ref not in {"HEAD"} and not base_ref.startswith(("origin/", "refs/")):
        candidate = f"origin/{base_ref}"
        if _rev_parse_ok(candidate):
            return candidate

    raise RuntimeError(f"Base ref not found: {base_ref}")


def resolve_worktree_base_ref(*, repo_dir: Path, cfg: Dict[str, Any], override: Optional[str] = None) -> str:
    """Resolve the logical base ref for session worktree creation.

    - If override is provided, it wins.
    - If cfg.baseBranchMode == "fixed", baseBranch is used (fallback: "main").
    - Otherwise, the current primary worktree HEAD ref is used.

    The returned ref is the value that should be recorded into session git metadata
    as `baseBranch` for stable downstream diffs and evidence.
    """
    if override:
        return str(override)
    mode_raw = cfg.get("baseBranchMode")
    if mode_raw:
        base_mode = str(mode_raw)
    else:
        # Backward-compatible inference:
        # - if a baseBranch is explicitly configured, treat it as fixed
        # - otherwise default to current primary HEAD
        base_mode = "fixed" if cfg.get("baseBranch") not in (None, "") else "current"
    if base_mode == "fixed":
        return str(cfg.get("baseBranch") or "main")
    return _resolve_current_base_ref(repo_dir)


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
    repo_dir = get_repo_dir()
    config_obj = _config()
    config = config_obj.get_worktree_config()
    if not config.get("enabled", False):
        return (None, None)

    worktree_path, branch_name = _resolve_worktree_target(session_id, config)
    base_branch_value = resolve_worktree_base_ref(repo_dir=repo_dir, cfg=config, override=base_branch)

    existing_wt = get_existing_worktree_path(branch_name)
    if existing_wt is not None:
        resolved = existing_wt.resolve()
        if not dry_run:
            _ensure_shared_sessions_dir(worktree_path=resolved, repo_dir=repo_dir)
            _ensure_worktree_session_id_file(worktree_path=resolved, session_id=session_id)
        return (resolved, branch_name)

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
        # If the configured target exists and is non-empty, choose a sibling path
        # (never fall back to hardcoded directories).
        if worktree_path.exists() and any(worktree_path.iterdir()):
            suffix_length = config_obj.get_worktree_uuid_suffix_length()
            base_parent = worktree_path.parent
            base_name = worktree_path.name
            # Avoid infinite loops if collisions persist
            for _ in range(5):
                candidate = base_parent / f"{base_name}-{uuid.uuid4().hex[:suffix_length]}"
                if not candidate.exists():
                    worktree_path = candidate
                    break
                if not any(candidate.iterdir()):
                    worktree_path = candidate
                    break
    except Exception:
        # Best effort only; the subsequent git command will fail with a clear error.
        pass

    base_dir_full = worktree_path.parent
    ensure_directory(base_dir_full)

    last_err: Optional[Exception] = None

    # Timeouts
    t_fetch = config_obj.get_worktree_timeout("fetch", 60)
    t_add = config_obj.get_worktree_timeout("worktree_add", 30)
    t_install = config_obj.get_worktree_timeout("install", 300)
    t_health = config_obj.get_worktree_timeout("health_check", 10)
    t_branch = config_obj.get_worktree_timeout("branch_check", 10)

    primary_before = _primary_head_marker(repo_dir)

    def _ref_exists(ref: str) -> bool:
        rr = run_with_timeout(
            ["git", "show-ref", "--verify", ref],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=config_obj.get_worktree_timeout("branch_check", 10),
        )
        return rr.returncode == 0

    # Resolve the base ref without mutating the primary checkout (do not checkout/pull).
    start_ref = _resolve_start_ref(repo_dir, base_branch_value, timeout=t_branch)

    for attempt in range(2):
        try:
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)

            branch_ref = f"refs/heads/{branch_name}"
            if _ref_exists(branch_ref):
                run_with_timeout(
                    ["git", "worktree", "add", "--", str(worktree_path), branch_name],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
            else:
                run_with_timeout(
                    ["git", "worktree", "add", "-b", branch_name, "--", str(worktree_path), start_ref],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            run_with_timeout(["git", "worktree", "prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=config_obj.get_worktree_timeout("prune", 10))
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)
    if last_err is not None:
        raise RuntimeError(f"Failed to create worktree after retries: {last_err}")

    install_flag = config.get("installDeps", False) if install_deps is None else bool(install_deps)
    if install_flag:
        def _resolve_install_cmd(cwd: Path) -> list[str]:
            """Pick an install command that avoids mutating lockfiles.

            Session worktrees are meant to isolate code changes. A plain
            package-manager install can normalize or rewrite lockfiles, creating
            noisy diffs and triggering unrelated security/audit validation.
            """
            if (cwd / "pnpm-lock.yaml").exists():
                return ["pnpm", "install", "--frozen-lockfile"]
            if (cwd / "package-lock.json").exists():
                return ["npm", "ci"]
            if (cwd / "yarn.lock").exists():
                return ["yarn", "install", "--immutable"]
            if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
                return ["bun", "install", "--frozen-lockfile"]
            # Best-effort fallback: keep previous behavior.
            return ["pnpm", "install"]

        def _resolve_fallback_install_cmd(cwd: Path) -> list[str] | None:
            """Fallback install command when immutable install is insufficient.

            Used when post-install commands fail due to missing binaries/build artefacts.
            """
            if (cwd / "pnpm-lock.yaml").exists():
                return ["pnpm", "install"]
            if (cwd / "package-lock.json").exists():
                return ["npm", "install"]
            if (cwd / "yarn.lock").exists():
                return ["yarn", "install"]
            if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
                return ["bun", "install"]
            return None

        def _run_install(cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
            try:
                return run_with_timeout(
                    cmd,
                    cwd=worktree_path,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=t_install,
                )
            except Exception:
                return None

        install_cmd = _resolve_install_cmd(worktree_path)
        fallback_cmd = _resolve_fallback_install_cmd(worktree_path)
        used_fallback = False

        result = _run_install(install_cmd)
        if fallback_cmd and (result is None or getattr(result, "returncode", 1) != 0):
            used_fallback = True
            _run_install(fallback_cmd)

        post_install = config.get("postInstallCommands", []) or []
        if isinstance(post_install, list) and post_install:
            commands = [str(c) for c in post_install if str(c).strip()]
            try:
                _run_post_install_commands(
                    worktree_path=worktree_path,
                    commands=commands,
                    timeout=t_install,
                )
            except Exception:
                # If immutable install didn't materialize enough for post-install steps,
                # retry once with a best-effort install command.
                if fallback_cmd and not used_fallback and fallback_cmd != install_cmd:
                    used_fallback = True
                    _run_install(fallback_cmd)
                    _run_post_install_commands(
                        worktree_path=worktree_path,
                        commands=commands,
                        timeout=t_install,
                    )
                else:
                    raise

    try:
        hc1 = run_with_timeout(["git", "rev-parse", "--is-inside-work-tree"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        hc2 = run_with_timeout(["git", "branch", "--show-current"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        if (hc1.stdout or "").strip() != "true" or (hc2.stdout or "").strip() != branch_name:
            raise RuntimeError("Worktree health check failed")

        git_file = worktree_path / ".git"
        if not git_file.exists():
            raise RuntimeError("Worktree missing .git metadata")
        if not git_file.is_file():
            raise RuntimeError("Expected a git worktree (.git must be a file), but got a non-worktree checkout")

        content = git_file.read_text(encoding="utf-8", errors="ignore")
        if "gitdir:" not in content:
            raise RuntimeError("Worktree .git file is missing gitdir pointer")
        target_raw = content.split("gitdir:", 1)[1].strip()
        target_path = Path(target_raw)
        if not target_path.is_absolute():
            target_path = (worktree_path / target_path).resolve()
        if not target_path.exists():
            raise RuntimeError(f"Worktree .git pointer is invalid: {target_raw}")
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    _ensure_shared_sessions_dir(worktree_path=worktree_path, repo_dir=repo_dir)
    _ensure_worktree_session_id_file(worktree_path=worktree_path, session_id=session_id)

    primary_after = _primary_head_marker(repo_dir)
    if primary_before != primary_after:
        raise RuntimeError(
            f"Primary worktree HEAD changed during worktree creation: {primary_before} -> {primary_after}"
        )

    return (worktree_path, branch_name)


def _run_post_install_commands(*, worktree_path: Path, commands: list[str], timeout: int) -> None:
    """Run project-configured post-install commands inside the worktree.

    This is a project-specific extension point (e.g., Prisma generation) that must
    be configuration-driven to keep Edison core generic.
    """
    for cmd in commands:
        result = run_with_timeout(
            ["bash", "-lc", cmd],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            tail_out = "\n".join((result.stdout or "").splitlines()[-25:])
            tail_err = "\n".join((result.stderr or "").splitlines()[-25:])
            raise RuntimeError(
                "Post-install command failed in worktree:\n"
                f"  cwd: {worktree_path}\n"
                f"  cmd: {cmd}\n"
                f"  exit: {result.returncode}\n"
                f"  stdout (tail):\n{tail_out}\n"
                f"  stderr (tail):\n{tail_err}"
            )


def restore_worktree(session_id: str, *, base_branch: Optional[str] = None, dry_run: bool = False) -> Path:
    """Restore a worktree from archive directory back to active worktrees.

    Note: Since archive_worktree removes the worktree from git's tracking,
    we need to delete the archived directory and re-create the worktree
    using create_worktree. This ensures proper git registration.
    """
    repo_dir = get_repo_dir()
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
    *,
    base_branch: Optional[str] = None,
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

    resolved_base = base_branch or cfg.get("baseBranch")
    if resolved_base is not None:
        git_meta["baseBranch"] = resolved_base

    return git_meta
