"""Worktree-local git excludes utilities.

Git ignores are repo-wide, but worktrees often need worktree-specific excludes
to keep local-first state (e.g. `.project/*` symlinks) from polluting `git status`
in code worktrees.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from edison.core.utils.io import ensure_lines_present
from edison.core.utils.subprocess import run_with_timeout


def _git_dir_for_checkout(checkout_path: Path) -> Path:
    """Return absolute git dir for the repository containing checkout_path."""
    cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-dir"],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    return Path((cp.stdout or "").strip()).resolve()


def ensure_worktree_excludes(checkout_path: Path, patterns: Iterable[str]) -> bool:
    """Ensure patterns exist in this checkout's worktree-local git exclude file.

    Writes to: `<gitdir>/info/exclude` (worktree-specific; not repo `.gitignore`).

    Returns:
        True if the exclude file changed.
    """
    required: List[str] = [str(p).strip() for p in patterns if str(p).strip()]
    if not required:
        return False

    git_dir = _git_dir_for_checkout(checkout_path)
    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    return ensure_lines_present(
        exclude_path,
        required,
        create=True,
        ensure_blank_line_before=True,
        ensure_trailing_newline=True,
    )


__all__ = ["ensure_worktree_excludes"]

