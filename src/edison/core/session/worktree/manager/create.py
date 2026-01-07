"""Worktree creation and restoration helpers."""

from __future__ import annotations

import shutil
import subprocess
import uuid
import os
import sys
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, Optional, cast

from edison.core.utils.git.worktree import get_existing_worktree_path, get_worktree_parent
from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout

from ..._utils import get_repo_dir
from ..config_helpers import _config, _resolve_archive_directory, _resolve_worktree_target
from .meta_setup import ensure_checkout_git_excludes
from .refs import _primary_head_marker, _resolve_start_ref, resolve_worktree_base_ref
from .session_id import _ensure_worktree_session_id_file
from .shared_config import shared_state_cfg
from .shared_paths import ensure_shared_paths_in_checkout
from .deps import maybe_install_deps_and_post_install
from .health import validate_worktree_checkout

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

    progress_enabled = os.environ.get("EDISON_SESSION_CREATE_PROGRESS") == "1"
    t0_total = perf_counter()

    def _progress(msg: str) -> None:
        if not progress_enabled:
            return
        print(f"[edison] {msg}", file=sys.stderr)

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
            _progress(f"Worktree exists for {branch_name}; reusing {resolved}")
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

    def _normalize_fetch_mode(raw: object) -> str:
        # Back-compat: treat booleans as explicit choices.
        if isinstance(raw, bool):
            return "always" if raw else "never"
        mode = str(raw or "on_failure").strip().lower()
        if mode in {"always", "never", "on_failure"}:
            return mode
        return "on_failure"

    fetch_mode = _normalize_fetch_mode(config.get("fetchMode"))

    def _fetch() -> None:
        _progress("Fetching remotes (git fetch --all --prune)...")
        run_with_timeout(
            ["git", "fetch", "--all", "--prune"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=t_fetch,
        )

    for _attempt in range(2):
        try:
            # Common case: baseBranchMode=current points at a local ref, so a fetch
            # is unnecessary and can hang when remotes are unreachable. Default to
            # fetching only on failure unless explicitly configured.
            if fetch_mode == "always" and _attempt == 0:
                _fetch()

            branch_ref = f"refs/heads/{branch_name}"
            if _ref_exists(branch_ref):
                _progress(f"Adding worktree checkout at {worktree_path} for existing branch {branch_name}...")
                t0_add = perf_counter()
                run_with_timeout(
                    ["git", "worktree", "add", "--", str(worktree_path), branch_name],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
                _progress(f"Worktree add completed in {perf_counter() - t0_add:0.2f}s")
            else:
                _progress(f"Adding worktree checkout at {worktree_path} ({branch_name} from {start_ref})...")
                t0_add = perf_counter()
                run_with_timeout(
                    ["git", "worktree", "add", "-b", branch_name, "--", str(worktree_path), start_ref],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
                _progress(f"Worktree add completed in {perf_counter() - t0_add:0.2f}s")
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            last_err = e
            _progress(f"Worktree add failed; pruning and retrying (attempt {_attempt + 1}/2)...")
            run_with_timeout(
                ["git", "worktree", "prune"],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=config_obj.get_worktree_timeout("prune", 10),
            )
            if fetch_mode in {"always", "on_failure"}:
                _fetch()
    if last_err is not None:
        raise RuntimeError(f"Failed to create worktree after retries: {last_err}")

    t0_install = perf_counter()
    maybe_install_deps_and_post_install(
        worktree_path=worktree_path,
        config=config,
        install_deps_override=install_deps,
        timeout=t_install,
    )
    if perf_counter() - t0_install > 0.5:
        _progress(f"Post-checkout steps completed in {perf_counter() - t0_install:0.2f}s")

    try:
        validate_worktree_checkout(worktree_path=worktree_path, branch_name=branch_name, timeout=t_health)
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    _progress("Linking shared paths + git excludes...")
    ensure_shared_paths_in_checkout(checkout_path=worktree_path, repo_dir=repo_dir, cfg=config, scope="session")
    _ensure_worktree_session_id_file(worktree_path=worktree_path, session_id=session_id)
    ensure_checkout_git_excludes(checkout_path=worktree_path, cfg=config, scope="session")
    _maybe_align_primary_shared_state()

    primary_after = _primary_head_marker(repo_dir)
    if primary_before != primary_after:
        raise RuntimeError(
            f"Primary worktree HEAD changed during worktree creation: {primary_before} -> {primary_after}"
        )

    _progress(f"Worktree ready in {perf_counter() - t0_total:0.2f}s: {worktree_path}")
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
