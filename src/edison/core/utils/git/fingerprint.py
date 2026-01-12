"""Git-based code fingerprint utilities.

These helpers provide a lightweight, deterministic fingerprint of the current
repo state for evidence freshness checks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edison.core.utils.subprocess import run_git_command

from .repository import get_git_root, get_repo_root, is_git_repository
from .status import get_status


_EXCLUDED_PREFIXES = (
    ".project/",
    ".edison/",
    ".agents/",
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
    if repo_root is None:
        root = Path(get_repo_root())
    else:
        # When an explicit root is provided, never fall back to the global
        # project root. Evidence snapshots must be keyed to the caller's
        # requested repo/worktree even when it's not a git repository.
        root = Path(repo_root).resolve()
        git_root = get_git_root(root)
        if git_root is not None:
            root = Path(git_root)

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
    #
    # We exclude:
    # - `.project/` (tasks, sessions, QA reports, evidence snapshots)
    # - `.edison/` (generated prompts / metadata in many repos)
    # - `.agents/` (agent configs/scripts in some repos)
    pathspec = ["--", ".", ":(exclude).project", ":(exclude).edison", ":(exclude).agents"]

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


@dataclass(frozen=True, slots=True)
class WorkspaceFingerprint:
    """Workspace fingerprint built from multiple git repositories + extra files."""

    git_head: str
    diff_hash: str
    git_dirty: bool
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "gitHead": self.git_head,
            "diffHash": self.diff_hash,
            "gitDirty": bool(self.git_dirty),
            "details": self.details,
        }


def _hash_file(path: Path) -> str:
    try:
        data = path.read_bytes()
    except Exception:
        data = b""
    return hashlib.sha256(data).hexdigest()


def compute_workspace_fingerprint(
    *,
    git_roots: list[Path],
    extra_files: list[Path] | None = None,
) -> dict[str, Any]:
    """Compute a deterministic fingerprint for a multi-repo workspace.

    This is useful for "meta repos" or workspaces where the actual changes happen
    in nested git repos (e.g., a components/ layout), but evidence is captured
    from a top-level orchestrator repo.
    """
    roots = [Path(p).resolve() for p in (git_roots or [])]
    files = [Path(p).resolve() for p in (extra_files or [])]

    root_fps: list[dict[str, Any]] = []
    dirty_any = False
    for root in roots:
        fp = compute_repo_fingerprint(root)
        dirty_any = dirty_any or bool(fp.get("gitDirty", False))
        root_fps.append(
            {
                "root": str(root),
                "gitHead": str(fp.get("gitHead") or ""),
                "diffHash": str(fp.get("diffHash") or ""),
                "gitDirty": bool(fp.get("gitDirty", False)),
            }
        )

    file_fps: list[dict[str, Any]] = []
    for p in files:
        # Only hash existing regular files; missing paths should not explode.
        if not p.exists() or not p.is_file():
            continue
        file_fps.append({"path": str(p), "sha256": _hash_file(p)})

    # Stable ordering so fingerprints don't depend on list ordering.
    root_fps_sorted = sorted(root_fps, key=lambda d: d.get("root", ""))
    file_fps_sorted = sorted(file_fps, key=lambda d: d.get("path", ""))

    payload_parts: list[str] = []
    for r in root_fps_sorted:
        payload_parts.append(f"root={r.get('root','')}")
        payload_parts.append(f"head={r.get('gitHead','')}")
        payload_parts.append(f"diff={r.get('diffHash','')}")
        payload_parts.append(f"dirty={int(bool(r.get('gitDirty', False)))}")
    for f in file_fps_sorted:
        payload_parts.append(f"file={f.get('path','')}")
        payload_parts.append(f"sha256={f.get('sha256','')}")

    payload = "\n".join(payload_parts).encode("utf-8")
    workspace_hash = hashlib.sha256(payload).hexdigest()

    # For snapshot directory names we need a short-ish stable "head".
    # Use a derived head when there are multiple roots.
    if len(root_fps_sorted) == 1:
        head = root_fps_sorted[0].get("gitHead") or "unknown-head"
    else:
        head = f"workspace-{workspace_hash[:12]}"

    details = {"gitRoots": root_fps_sorted, "extraFiles": file_fps_sorted}
    return WorkspaceFingerprint(git_head=head, diff_hash=workspace_hash, git_dirty=dirty_any, details=details).as_dict()


__all__ = ["WorkspaceFingerprint", "compute_repo_fingerprint", "compute_workspace_fingerprint"]
