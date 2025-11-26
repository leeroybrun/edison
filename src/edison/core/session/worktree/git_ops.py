"""Git operations for worktree management."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from edison.core.utils.subprocess import run_with_timeout
from edison.core.paths.resolver import PathResolver
from .config_helpers import _config, _get_repo_dir


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
