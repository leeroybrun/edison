"""Session presentation helpers (shared between multiple CLI commands).

This module centralizes user-facing session/worktree messaging so commands like
`edison session create` and `edison session status` stay consistent without
duplicating formatting logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorktreePresentation:
    worktree_path: str | None
    branch_name: str | None
    base_branch: str | None
    worktree_pinned: bool
    session_id_file_path: str | None


def _worktree_pinning(*, session_id: str, worktree_path: str | None) -> tuple[bool, str | None]:
    if not worktree_path:
        return False, None
    try:
        from edison.core.session.worktree.manager import get_worktree_pinning_status

        status = get_worktree_pinning_status(Path(worktree_path), session_id)
        return bool(status.get("worktreePinned", False)), status.get("sessionIdFilePath")
    except Exception:
        return False, None


def build_worktree_presentation(*, session_id: str, session: dict[str, Any]) -> WorktreePresentation:
    git = session.get("git") if isinstance(session.get("git"), dict) else {}
    worktree_path = git.get("worktreePath")
    branch_name = git.get("branchName")
    base_branch = git.get("baseBranch")

    pinned, session_id_file_path = _worktree_pinning(session_id=session_id, worktree_path=worktree_path)
    return WorktreePresentation(
        worktree_path=str(worktree_path) if worktree_path else None,
        branch_name=str(branch_name) if branch_name else None,
        base_branch=str(base_branch) if base_branch else None,
        worktree_pinned=pinned,
        session_id_file_path=str(session_id_file_path) if session_id_file_path else None,
    )


def worktree_confinement_lines(*, session_id: str, worktree_path: str | None) -> list[str]:
    if not worktree_path:
        return []
    return [
        "WORKTREE CONFINEMENT (CRITICAL)",
        f"  cd {worktree_path}",
        f"  export AGENTS_SESSION={session_id}",
        f"  export AGENTS_PROJECT_ROOT={worktree_path}",
        "  Never run `git checkout` / `git switch` in the primary checkout.",
        "  Never run `git reset` / `git restore` / `git clean` unless explicitly requested.",
        "  Do all code changes inside the session worktree directory only.",
    ]


__all__ = ["WorktreePresentation", "build_worktree_presentation", "worktree_confinement_lines"]

