"""Worktree checkout validation helpers."""

from __future__ import annotations

from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout


def validate_worktree_checkout(*, worktree_path: Path, branch_name: str, timeout: int) -> None:
    hc1 = run_with_timeout(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    hc2 = run_with_timeout(
        ["git", "branch", "--show-current"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
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

