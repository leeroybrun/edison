"""Worktree session-id pinning helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import ensure_directory


def _ensure_worktree_session_id_file(*, worktree_path: Path, session_id: str) -> None:
    """Ensure `<project-management-dir>/.session-id` exists inside the worktree."""
    try:
        from edison.core.utils.paths import PathResolver
        from edison.core.utils.paths.management import ProjectManagementPaths

        repo_root = PathResolver.resolve_project_root()
        mgmt_dir_name = ProjectManagementPaths(repo_root).get_management_root().name
        project_dir = worktree_path / mgmt_dir_name
        ensure_directory(project_dir)
        target = project_dir / ".session-id"
        try:
            if target.exists() and target.read_text(encoding="utf-8").strip() == session_id:
                return
        except Exception:
            pass
        target.write_text(session_id + "\n", encoding="utf-8")
    except Exception:
        return


def ensure_worktree_session_id_file(*, worktree_path: Path, session_id: str) -> None:
    _ensure_worktree_session_id_file(worktree_path=worktree_path, session_id=session_id)


def get_worktree_session_id_file_path(worktree_path: Path) -> Optional[Path]:
    try:
        from edison.core.utils.paths import PathResolver
        from edison.core.utils.paths.management import ProjectManagementPaths

        repo_root = PathResolver.resolve_project_root()
        mgmt_dir_name = ProjectManagementPaths(repo_root).get_management_root().name
        return worktree_path / mgmt_dir_name / ".session-id"
    except Exception:
        return None


def get_worktree_pinning_status(worktree_path: Optional[Path], session_id: str) -> Dict[str, Any]:
    if worktree_path is None:
        return {"sessionIdFilePath": None, "worktreePinned": False}

    session_id_file = get_worktree_session_id_file_path(Path(worktree_path))
    if session_id_file is None:
        return {"sessionIdFilePath": None, "worktreePinned": False}

    pinned = False
    try:
        if session_id_file.exists():
            content = session_id_file.read_text(encoding="utf-8").strip()
            pinned = content == session_id
    except Exception:
        pinned = False

    return {"sessionIdFilePath": str(session_id_file), "worktreePinned": pinned}


__all__ = [
    "ensure_worktree_session_id_file",
    "get_worktree_pinning_status",
    "get_worktree_session_id_file_path",
    "_ensure_worktree_session_id_file",
]

