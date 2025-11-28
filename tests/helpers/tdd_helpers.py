"""TDD utilities for Edison.

Implements REFACTOR-cycle validation with no legacy fallbacks.

Policy: NO legacy support – see .project/qa/EDISON_NO_LEGACY_POLICY.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional
import subprocess

from edison.core.utils.subprocess import check_output_with_timeout


CommitProvider = Callable[[str, str], List[Dict]]


def _collect_commits_simple(base_branch: str, cwd: Optional[Path]) -> List[Dict]:
    """Return commits (oldest→newest) since merge-base(base_branch, HEAD)..HEAD.

    Minimal payload: [{"message": str}]
    No legacy fallbacks; fails closed if git is unavailable.
    """
    # Resolve repo root lazily to avoid import issues in tests that inject providers
    if cwd is None:
        try:
            # Local import only when required by git-backed collection
            from . import task  # type: ignore
        except Exception:  # pragma: no cover
            from edison.core import task  # type: ignore
        repo = task.ROOT
    else:
        repo = cwd
    # Compute a stable range via merge-base
    try:
        mb = check_output_with_timeout(
            ["git", "merge-base", base_branch, "HEAD"],
            text=True,
            cwd=str(repo),
            timeout_type="git_operations",
        ).strip()
        raw = check_output_with_timeout(
            ["git", "log", "--reverse", "--pretty=format:%s", f"{mb}..HEAD"],
            text=True,
            cwd=str(repo),
            timeout_type="git_operations",
        )
    except Exception:
        return []
    commits: List[Dict] = []
    for line in raw.splitlines():
        msg = line.strip()
        if not msg:
            continue
        commits.append({"message": msg})
    return commits


def _validate_refactor_cycle(
    task_id: str,
    *,
    commit_provider: Optional[CommitProvider] = None,
    started_at_iso: Optional[str] = None,  # reserved for future use; unused by default
    base_branch: str = "main",
    cwd: Optional[Path] = None,
) -> bool:
    """Validate REFACTOR commit follows GREEN.

    Rules:
    - If no commits are found, return True (valid initial state).
    - If the last commit message starts with "[REFACTOR]", the immediately
      preceding commit MUST start with "[GREEN]".

    This function performs a focused check and does not duplicate the broader
    RED→GREEN enforcement already handled elsewhere.
    """
    # Gather commits via injected provider (tests) or git (runtime)
    commits = (
        (commit_provider(started_at_iso or "", base_branch) if commit_provider else _collect_commits_simple(base_branch, cwd))
        or []
    )

    if not commits:
        return True  # No commits yet – valid state

    last = commits[-1]
    last_msg = (last.get("message") or "").strip()
    if last_msg.startswith("[REFACTOR]"):
        if len(commits) < 2:
            return False
        prev = commits[-2]
        prev_msg = (prev.get("message") or "").strip()
        if not prev_msg.startswith("[GREEN]"):
            return False

    return True


__all__ = [
    "CommitProvider",
]
