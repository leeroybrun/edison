"""Git-based code fingerprint utilities.

These helpers provide a lightweight, deterministic fingerprint of the current
repo state for evidence freshness checks.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from edison.core.utils.subprocess import run_git_command

from .repository import get_repo_root, is_git_repository
from .status import get_status


_EXCLUDED_PREFIXES = (
    ".project/",
)


def _filter_paths(paths: list[Any]) -> list[str]:
    out: list[str] = []
    for p in paths or []:
        s = str(p).strip().replace("\\", "/")
        if not s:
            continue
        if any(s.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
            continue
        out.append(s)
    return out


def compute_repo_fingerprint(repo_root: Path | str | None = None) -> dict[str, Any]:
    """Compute a lightweight fingerprint of the current repository state.

    Returns a dict with keys:
    - gitHead: current HEAD SHA (empty when unavailable)
    - gitDirty: whether the working tree has staged/modified/untracked changes
    - diffHash: sha256 over a stable representation of current diffs + file lists
    """
    root = get_repo_root(repo_root) if repo_root is not None else get_repo_root()
    root = Path(root)

    if not is_git_repository(root):
        # Deterministic empty fingerprint for non-git contexts.
        return {"gitHead": "", "gitDirty": False, "diffHash": hashlib.sha256(b"").hexdigest()}

    head = ""
    try:
        res = run_git_command(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        head = (res.stdout or "").strip()
    except Exception:
        head = ""

    status = get_status(root)

    staged_list = _filter_paths(status.get("staged") or [])
    modified_list = _filter_paths(status.get("modified") or [])
    untracked_list = _filter_paths(status.get("untracked") or [])
    dirty = bool(staged_list or modified_list or untracked_list)

    # Exclude Edison-managed metadata from the fingerprint to avoid making
    # evidence snapshots self-invalidating (writing evidence would otherwise
    # change the fingerprint and create an infinite chase).
    pathspec = ["--", ".", ":(exclude).project"]

    diff = ""
    diff_cached = ""
    try:
        diff = (
            run_git_command(
                ["git", "diff", "--no-ext-diff", *pathspec],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            or ""
        )
    except Exception:
        diff = ""
    try:
        diff_cached = (
            run_git_command(
                ["git", "diff", "--cached", "--no-ext-diff", *pathspec],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            or ""
        )
    except Exception:
        diff_cached = ""

    staged = "\n".join(sorted(staged_list))
    modified = "\n".join(sorted(modified_list))
    untracked = "\n".join(sorted(untracked_list))

    payload = "\n".join([head, diff, diff_cached, staged, modified, untracked]).encode("utf-8")
    diff_hash = hashlib.sha256(payload).hexdigest()

    return {"gitHead": head, "gitDirty": bool(dirty), "diffHash": diff_hash}


__all__ = ["compute_repo_fingerprint"]
