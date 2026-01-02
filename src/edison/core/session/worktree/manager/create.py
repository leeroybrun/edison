"""Worktree creation and restoration helpers."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, cast

from edison.core.utils.git.worktree import get_existing_worktree_path, get_worktree_parent
from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout

from .._utils import get_repo_dir
from ..config_helpers import _config, _resolve_archive_directory, _resolve_worktree_target
from .meta_setup import ensure_checkout_git_excludes
from .post_install import _run_post_install_commands
from .refs import _primary_head_marker, _resolve_start_ref, resolve_worktree_base_ref
from .session_id import _ensure_worktree_session_id_file
from .shared_config import shared_state_cfg
from .shared_paths import ensure_shared_paths_in_checkout

__all__ = [
    "create_worktree",
    "restore_worktree",
    "resolve_worktree_target",
    "ensure_worktree_materialized",
]


def resolve_worktree_target(session_id: str) -> tuple[Path, str]:
    """Public helper to compute target path/branch using current config."""
    cfg = _config().get_worktree_config()
    return _resolve_worktree_target(session_id, cfg)


def create_worktree(
    session_id: str,
    base_branch: Optional[str] = None,
    worktree_path_override: Optional[str] = None,
    install_deps: Optional[bool] = None,
    dry_run: bool = False,
) -> tuple[Optional[Path], Optional[str]]:
    """Create git worktree for session."""
    repo_dir = get_repo_dir()
    config_obj = _config()
    config = config_obj.get_worktree_config()
    if not config.get("enabled", False):
        return (None, None)

    def _maybe_align_primary_shared_state() -> None:
        try:
            ss = shared_state_cfg(config)
            mode = str(ss.get("mode") or "meta").strip().lower()
            if mode != "meta":
                return
            primary_repo_dir = get_worktree_parent(repo_dir) or repo_dir
            ensure_shared_paths_in_checkout(
                checkout_path=primary_repo_dir,
                repo_dir=primary_repo_dir,
                cfg=config,
                scope="primary",
            )
            ensure_checkout_git_excludes(checkout_path=primary_repo_dir, cfg=config, scope="primary")
        except Exception:
            return

    worktree_path, branch_name = _resolve_worktree_target(session_id, config)
    if worktree_path_override:
        override = Path(str(worktree_path_override))
        if not override.is_absolute():
            override = ((get_worktree_parent(repo_dir) or repo_dir) / override).resolve()
        worktree_path = override
    base_branch_value = resolve_worktree_base_ref(repo_dir=repo_dir, cfg=config, override=base_branch)

    existing_wt = get_existing_worktree_path(branch_name)
    if existing_wt is not None:
        resolved = existing_wt.resolve()
        if not dry_run:
            ensure_shared_paths_in_checkout(
                checkout_path=resolved, repo_dir=repo_dir, cfg=config, scope="session"
            )
            _ensure_worktree_session_id_file(worktree_path=resolved, session_id=session_id)
            ensure_checkout_git_excludes(checkout_path=resolved, cfg=config, scope="session")
            _maybe_align_primary_shared_state()
        return (resolved, branch_name)

    # Fail fast when repo has no commits (unborn HEAD).
    try:
        run_with_timeout(
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
            suffix_length = config_obj.get_worktree_uuid_suffix_length()
            base_parent = worktree_path.parent
            base_name = worktree_path.name
            for _ in range(5):
                candidate = base_parent / f"{base_name}-{uuid.uuid4().hex[:suffix_length]}"
                if not candidate.exists():
                    worktree_path = candidate
                    break
                if not any(candidate.iterdir()):
                    worktree_path = candidate
                    break
    except Exception:
        pass

    ensure_directory(worktree_path.parent)

    last_err: Optional[Exception] = None

    t_fetch = config_obj.get_worktree_timeout("fetch", 60)
    t_add = config_obj.get_worktree_timeout("worktree_add", 30)
    t_install = config_obj.get_worktree_timeout("install", 300)
    t_health = config_obj.get_worktree_timeout("health_check", 10)
    t_branch = config_obj.get_worktree_timeout("branch_check", 10)

    primary_before = _primary_head_marker(repo_dir)

    def _ref_exists(ref: str) -> bool:
        rr = cast(
            subprocess.CompletedProcess[str],
            run_with_timeout(
                ["git", "show-ref", "--verify", ref],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=config_obj.get_worktree_timeout("branch_check", 10),
            ),
        )
        return rr.returncode == 0

    start_ref = _resolve_start_ref(repo_dir, base_branch_value, timeout=t_branch)

    for _attempt in range(2):
        try:
            run_with_timeout(
                ["git", "fetch", "--all", "--prune"],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=t_fetch,
            )

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
            run_with_timeout(
                ["git", "worktree", "prune"],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=config_obj.get_worktree_timeout("prune", 10),
            )
            run_with_timeout(
                ["git", "fetch", "--all", "--prune"],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=t_fetch,
            )
    if last_err is not None:
        raise RuntimeError(f"Failed to create worktree after retries: {last_err}")

    def _resolve_install_cmd(cwd: Path) -> list[str]:
        if (cwd / "pnpm-lock.yaml").exists():
            return ["pnpm", "install", "--frozen-lockfile"]
        if (cwd / "package-lock.json").exists():
            return ["npm", "ci"]
        if (cwd / "yarn.lock").exists():
            return ["yarn", "install", "--immutable"]
        if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
            return ["bun", "install", "--frozen-lockfile"]
        return ["pnpm", "install"]

    def _resolve_fallback_install_cmd(cwd: Path) -> list[str] | None:
        if (cwd / "pnpm-lock.yaml").exists():
            return ["pnpm", "install"]
        if (cwd / "package-lock.json").exists():
            return ["npm", "install"]
        if (cwd / "yarn.lock").exists():
            return ["yarn", "install"]
        if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
            return ["bun", "install"]
        return None

    def _tail(text: str, n: int = 25) -> str:
        lines = (text or "").splitlines()
        return "\n".join(lines[-n:])

    def _run_install(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return cast(
                subprocess.CompletedProcess[str],
                run_with_timeout(
                    cmd,
                    cwd=worktree_path,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=t_install,
                ),
            )
        except FileNotFoundError as e:
            bin_name = str(cmd[0]) if cmd else "unknown"
            raise RuntimeError(
                "Dependency install failed in worktree (command not found).\n"
                f"  cwd: {worktree_path}\n"
                f"  cmd: {' '.join(cmd)}\n"
                f"  missing: {bin_name}\n"
                "Fix: install the required package manager (pnpm/npm/yarn/bun), "
                "or set `worktrees.installDeps: false` in your project config."
            ) from e
        except Exception as e:
            raise RuntimeError(
                "Dependency install failed in worktree (runner error).\n"
                f"  cwd: {worktree_path}\n"
                f"  cmd: {' '.join(cmd)}\n"
                f"  error: {e}"
            ) from e

    def _ensure_install_ok(result: subprocess.CompletedProcess[str], *, cmd: list[str]) -> None:
        if result.returncode == 0:
            return
        raise RuntimeError(
            "Dependency install failed in worktree.\n"
            f"  cwd: {worktree_path}\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  exit: {result.returncode}\n"
            f"  stdout (tail):\n{_tail(result.stdout)}\n"
            f"  stderr (tail):\n{_tail(result.stderr)}"
        )

    install_flag = config.get("installDeps", False) if install_deps is None else bool(install_deps)
    fallback_cmd = _resolve_fallback_install_cmd(worktree_path)
    used_fallback = False

    if install_flag:
        install_cmd = _resolve_install_cmd(worktree_path)
        result = _run_install(install_cmd)
        if result.returncode != 0 and fallback_cmd:
            used_fallback = True
            fallback_result = _run_install(fallback_cmd)
            _ensure_install_ok(fallback_result, cmd=fallback_cmd)
        else:
            _ensure_install_ok(result, cmd=install_cmd)

    post_install = config.get("postInstallCommands", []) or []
    if isinstance(post_install, list) and post_install:
        commands = [str(c) for c in post_install if str(c).strip()]
        try:
            _run_post_install_commands(worktree_path=worktree_path, commands=commands, timeout=t_install)
        except Exception:
            if fallback_cmd and not used_fallback:
                used_fallback = True
                fallback_result = _run_install(fallback_cmd)
                _ensure_install_ok(fallback_result, cmd=fallback_cmd)
                _run_post_install_commands(
                    worktree_path=worktree_path, commands=commands, timeout=t_install
                )
            else:
                raise

    try:
        hc1 = run_with_timeout(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=t_health,
        )
        hc2 = run_with_timeout(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=t_health,
        )
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

    ensure_shared_paths_in_checkout(checkout_path=worktree_path, repo_dir=repo_dir, cfg=config, scope="session")
    _ensure_worktree_session_id_file(worktree_path=worktree_path, session_id=session_id)
    ensure_checkout_git_excludes(checkout_path=worktree_path, cfg=config, scope="session")
    _maybe_align_primary_shared_state()

    primary_after = _primary_head_marker(repo_dir)
    if primary_before != primary_after:
        raise RuntimeError(
            f"Primary worktree HEAD changed during worktree creation: {primary_before} -> {primary_after}"
        )

    return (worktree_path, branch_name)


def restore_worktree(
    session_id: str,
    *,
    source: Optional[str] = None,
    base_branch: Optional[str] = None,
    dry_run: bool = False,
) -> Path:
    repo_dir = get_repo_dir()
    cfg = _config().get_worktree_config()

    worktree_path, _branch_name = _resolve_worktree_target(session_id, cfg)
    archive_full = _resolve_archive_directory(cfg, repo_dir)
    src_root = archive_full
    if source:
        p = Path(str(source))
        if not p.is_absolute():
            p = ((get_worktree_parent(repo_dir) or repo_dir) / p).resolve()
        src_root = p
    src = src_root if src_root.name == session_id else (src_root / session_id)
    if not src.exists():
        raise RuntimeError(f"Archived worktree not found: {src}")

    if dry_run:
        return worktree_path

    shutil.rmtree(src, ignore_errors=True)

    created_path, _created_branch = create_worktree(
        session_id=session_id,
        base_branch=base_branch,
        dry_run=False,
    )

    if created_path != worktree_path:
        raise RuntimeError(f"Restored worktree path mismatch: expected {worktree_path}, got {created_path}")

    return worktree_path


def ensure_worktree_materialized(session_id: str) -> Dict[str, Any]:
    path, branch = create_worktree(session_id)
    if path and branch:
        return {"worktreePath": str(path), "branchName": branch}
    return {}
