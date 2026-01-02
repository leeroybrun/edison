"""Worktree ref/base resolution helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, cast

from edison.core.utils.subprocess import run_with_timeout

from ..config_helpers import _config


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
    """Resolve a start ref that can be passed to `git worktree add`."""

    def _rev_parse_ok(ref: str) -> bool:
        rr = cast(
            subprocess.CompletedProcess[str],
            run_with_timeout(
                ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
        )
        return rr.returncode == 0

    if _rev_parse_ok(base_ref):
        return base_ref

    if base_ref not in {"HEAD"} and not base_ref.startswith(("origin/", "refs/")):
        candidate = f"origin/{base_ref}"
        if _rev_parse_ok(candidate):
            return candidate

    raise RuntimeError(f"Base ref not found: {base_ref}")


def resolve_worktree_base_ref(*, repo_dir: Path, cfg: Dict[str, Any], override: Optional[str] = None) -> str:
    """Resolve the logical base ref for session worktree creation."""
    if override:
        return str(override)
    mode_raw = cfg.get("baseBranchMode")
    if mode_raw:
        base_mode = str(mode_raw)
    else:
        base_mode = "fixed" if cfg.get("baseBranch") not in (None, "") else "current"
    if base_mode == "fixed":
        return str(cfg.get("baseBranch") or "main")
    return _resolve_current_base_ref(repo_dir)


__all__ = [
    "resolve_worktree_base_ref",
    "_primary_head_marker",
    "_resolve_start_ref",
]
