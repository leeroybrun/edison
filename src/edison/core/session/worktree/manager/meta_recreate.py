"""Meta shared-state reset/recreate helper."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.git.worktree import get_worktree_parent, is_worktree_registered
from edison.core.utils.subprocess import run_with_timeout

from .._utils import get_repo_dir
from ..config_helpers import _config
from .meta_init import initialize_meta_shared_state
from .meta_setup import ensure_meta_worktree_setup
from .meta_status import get_meta_worktree_status
from .shared_config import parse_shared_paths, shared_state_cfg


def recreate_meta_shared_state(
    *,
    repo_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Recreate the meta branch/worktree as an orphan branch, preserving configured shared state."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = get_meta_worktree_status(repo_dir=root)
    status["mode"] = mode
    if mode != "meta":
        return status

    primary_repo_dir = Path(status["primary_repo_dir"])
    meta_path = Path(status["meta_path"])
    branch = str(status["meta_branch"])

    if dry_run:
        status["recreated"] = True
        return status

    shared_paths = [
        p
        for p in parse_shared_paths(cfg)
        if str(p.get("targetRoot") or "shared").lower() == "shared"
    ]

    # Refuse to recreate if the meta branch is checked out in other worktrees.
    cp = run_with_timeout(
        ["git", "worktree", "list", "--porcelain"],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=int(_config().get_worktree_timeout("health_check", 10)),
    )
    current: Optional[Path] = None
    current_branch: Optional[str] = None
    for line in (cp.stdout or "").splitlines():
        if line.startswith("worktree "):
            current = Path(line.split(" ", 1)[1].strip())
            current_branch = None
            continue
        if line.startswith("branch "):
            current_branch = line.split(" ", 1)[1].strip()
            continue
        if not line.strip():
            if current is not None and current_branch == f"refs/heads/{branch}":
                p = current.resolve()
                if p != meta_path.resolve():
                    raise RuntimeError(
                        f"Refusing to recreate meta branch; it is checked out elsewhere: {p}"
                    )
            current = None
            current_branch = None

    snapshot_dir: Optional[Path] = None

    def _snapshot_item(*, src: Path, dest: Path) -> None:
        if src.is_symlink():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            dest.symlink_to(os.readlink(src), target_is_directory=src.is_dir())
            return

        if src.is_dir():
            shutil.copytree(
                src,
                dest,
                dirs_exist_ok=True,
                symlinks=True,
                ignore_dangling_symlinks=True,
            )
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    if meta_path.exists():
        if not is_worktree_registered(meta_path, repo_root=primary_repo_dir):
            raise RuntimeError(
                "Meta path exists but is not a registered worktree; refusing to recreate. "
                f"Path: {meta_path}"
            )

        # Fail closed if the meta branch currently tracks files outside the preserved prefixes.
        tracked_allowed = [".project/"]
        for item in shared_paths:
            raw = str(item.get("path") or "").strip()
            if not raw:
                continue
            tracked_allowed.append(raw.rstrip("/") + "/")
            tracked_allowed.append(raw.rstrip("/"))
        try:
            ls = run_with_timeout(
                ["git", "ls-tree", "-r", "--name-only", "HEAD"],
                cwd=meta_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=int(_config().get_worktree_timeout("health_check", 10)),
            )
            tracked_files = [p.strip() for p in (ls.stdout or "").splitlines() if p.strip()]
            unexpected = [
                p
                for p in tracked_files
                if not any(p.startswith(prefix) for prefix in tracked_allowed)
            ]
            if unexpected and not force:
                sample = ", ".join(unexpected[:10])
                raise RuntimeError(
                    "Refusing to recreate meta branch because it tracks files outside the preserved prefixes. "
                    f"Count={len(unexpected)}. Sample: {sample}. "
                    "Add paths to worktrees.sharedState.sharedPaths or re-run with --force to discard."
                )
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("Failed to inspect tracked files in meta worktree; refusing to recreate.")

        # Fail closed if there are local changes outside of the shared state we will preserve.
        allowed_prefixes = [".project/", ".edison/_generated/"]
        for item in shared_paths:
            raw = str(item.get("path") or "").strip()
            if not raw:
                continue
            allowed_prefixes.append(raw.rstrip("/") + "/")
            allowed_prefixes.append(raw.rstrip("/"))

        st = run_with_timeout(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=meta_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )
        unsafe: list[str] = []
        for line in (st.stdout or "").splitlines():
            if not line.strip():
                continue
            path_part = line[3:].strip()
            for part in [p.strip() for p in path_part.split(" -> ") if p.strip()]:
                if not any(part.startswith(prefix) for prefix in allowed_prefixes):
                    unsafe.append(part)
        if unsafe and not force:
            raise RuntimeError(
                "Refusing to recreate meta worktree with local changes outside shared state. "
                f"Re-run with --force to discard: {', '.join(sorted(set(unsafe)))}"
            )

        # Snapshot shared state before removal to avoid data loss.
        snapshot_dir = Path(tempfile.mkdtemp(prefix="edison-meta-shared-state-"))
        try:
            for item in shared_paths:
                raw = str(item.get("path") or "").strip()
                if not raw:
                    continue
                p = Path(raw)
                if p.is_absolute() or ".." in p.parts:
                    continue
                src = meta_path / str(p)
                if not src.exists():
                    continue
                dest = snapshot_dir / str(p)
                _snapshot_item(src=src, dest=dest)
        except Exception:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            raise

        run_with_timeout(
            ["git", "worktree", "remove", "--force", str(meta_path)],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("worktree_add", 30)),
        )

    show = run_with_timeout(
        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=False,
        timeout=int(_config().get_worktree_timeout("health_check", 10)),
    )
    if show.returncode == 0:
        run_with_timeout(
            ["git", "update-ref", "-d", f"refs/heads/{branch}"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )

    from .meta_worktree import _create_orphan_branch

    _create_orphan_branch(
        repo_dir=primary_repo_dir,
        branch=branch,
        timeout=int(_config().get_worktree_timeout("health_check", 10)),
    )
    run_with_timeout(
        ["git", "worktree", "add", str(meta_path), branch],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=int(_config().get_worktree_timeout("worktree_add", 30)),
    )
    ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)

    if snapshot_dir is not None:
        try:
            shutil.copytree(
                snapshot_dir,
                meta_path,
                dirs_exist_ok=True,
                symlinks=True,
                ignore_dangling_symlinks=True,
            )
        finally:
            shutil.rmtree(snapshot_dir, ignore_errors=True)

    init = initialize_meta_shared_state(
        repo_dir=get_worktree_parent(primary_repo_dir) or primary_repo_dir,
        dry_run=False,
    )
    init["recreated"] = True
    return init


__all__ = ["recreate_meta_shared_state"]

