"""Low-level meta worktree creation/inspection helpers.

This module intentionally avoids dependencies on "shared paths" logic so that it
can be used by higher-level orchestration without import cycles.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from edison.core.config.domains.project import ProjectConfig
from edison.core.utils.git.worktree import get_worktree_parent, is_worktree_registered
from edison.core.utils.subprocess import run_with_timeout

from ..._utils import get_repo_dir
from .shared_config import shared_state_cfg


def _create_orphan_branch(*, repo_dir: Path, branch: str, timeout: int) -> str:
    """Create an orphan branch with a single empty root commit, without checking it out."""
    empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    cp = run_with_timeout(
        ["git", "commit-tree", empty_tree, "-m", "Initialize Edison meta branch"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    sha = (cp.stdout or "").strip()
    if not sha:
        raise RuntimeError(f"Failed to create orphan commit for branch {branch}")
    run_with_timeout(
        ["git", "update-ref", f"refs/heads/{branch}", sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return sha


def resolve_meta_worktree_path(*, cfg: Dict[str, Any], repo_dir: Path) -> Path:
    """Resolve meta worktree path from config."""
    ss = shared_state_cfg(cfg)
    raw = ss.get("metaPathTemplate") or ".worktrees/_meta"
    substituted = ProjectConfig(repo_root=repo_dir).substitute_project_tokens(str(raw))
    p = Path(substituted)
    if p.is_absolute():
        return p
    return (repo_dir / p).resolve()


def ensure_meta_worktree_checkout(
    *,
    repo_dir: Optional[Path] = None,
    cfg: Dict[str, Any],
    dry_run: bool = False,
) -> Tuple[Path, str, bool]:
    """Ensure the shared-state meta worktree exists and return (path, branch, created)."""
    root = repo_dir or get_repo_dir()
    ss = shared_state_cfg(cfg)
    branch = str(ss.get("metaBranch") or "edison-meta")

    primary_repo_dir = get_worktree_parent(root) or root
    meta_path = resolve_meta_worktree_path(cfg=cfg, repo_dir=primary_repo_dir)

    # If we're already inside the meta worktree, treat it as existing.
    try:
        if meta_path.resolve() == Path(root).resolve():
            return meta_path, branch, False
    except Exception:
        pass

    if dry_run:
        return meta_path, branch, False

    from ..config_helpers import _config

    timeout_add = int(_config().get_worktree_timeout("worktree_add", 30))
    timeout_health = int(_config().get_worktree_timeout("health_check", 10))

    # If the path exists, require it to be a git checkout (avoid clobbering).
    if meta_path.exists():
        try:
            if is_worktree_registered(meta_path, repo_root=primary_repo_dir):
                return meta_path, branch, False
        except Exception:
            pass
        try:
            cp = run_with_timeout(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=meta_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_health,
            )
            if (cp.stdout or "").strip() != "true":
                raise RuntimeError(f"Meta worktree path exists but is not a git worktree: {meta_path}")
        except Exception as e:
            raise RuntimeError(f"Meta worktree path exists but is not usable: {meta_path} ({e})")
        raise RuntimeError(
            "Meta worktree path exists but is not registered for this repository. "
            f"Path: {meta_path}. "
            "Set worktrees.sharedState.metaPathTemplate to a repo-unique location."
        )

    # Create (or attach) meta worktree without switching the primary checkout.
    created = False
    try:
        show = run_with_timeout(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_health,
        )
        if show.returncode == 0:
            run_with_timeout(
                ["git", "worktree", "add", str(meta_path), branch],
                cwd=primary_repo_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout_add,
            )
        else:
            _create_orphan_branch(repo_dir=primary_repo_dir, branch=branch, timeout=timeout_health)
            run_with_timeout(
                ["git", "worktree", "add", str(meta_path), branch],
                cwd=primary_repo_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout_add,
            )
            created = True
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        if "already exists" in stderr or "already exists" in stdout or "is already checked out" in stderr:
            try:
                if is_worktree_registered(meta_path, repo_root=primary_repo_dir):
                    return meta_path, branch, False
            except Exception:
                pass
            raise RuntimeError(
                "Meta worktree path already exists but is not registered for this repository. "
                f"Path: {meta_path}. "
                "Set worktrees.sharedState.metaPathTemplate to a repo-unique location."
            ) from exc
        raise RuntimeError(f"Failed to create meta worktree at {meta_path}: {stderr or stdout}") from exc

    return meta_path, branch, created


__all__ = [
    "ensure_meta_worktree_checkout",
    "resolve_meta_worktree_path",
]
