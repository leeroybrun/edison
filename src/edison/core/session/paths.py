"""Session path resolution utilities.

This module provides path resolution for session-scoped records (tasks, QA).
It extracts the session path discovery logic that was previously duplicated
in QARepository and TaskRepository.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths import PathResolver
from .core.layout import get_session_base_path


def get_session_bases(
    session_id: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> List[Path]:
    """Get session base paths to search for records.

    This function finds all possible session base directories where
    records (tasks, QA) might be stored. It handles both:
    - Specific session lookup (when session_id provided)
    - Discovery of all sessions (when session_id is None)

    Args:
        session_id: Optional session identifier to search for
        project_root: Optional project root (defaults to current project)

    Returns:
        List of session base directory paths (resolved, deduplicated)

    Examples:
        # Find all session directories
        bases = get_session_bases()

        # Find specific session directory
        bases = get_session_bases(session_id="sess-123")
    """
    # Lazy import to avoid circular dependency
    from edison.core.task.paths import get_session_dirs

    project_root = project_root or PathResolver.resolve_project_root()
    bases: List[Path] = []

    if session_id:
        # Specific session lookup
        session: Dict[str, Any] = {"id": session_id}
        session_path: Optional[Path] = None

        # Try to get session from repository
        try:
            from edison.core.session.persistence.repository import SessionRepository
            session_repo = SessionRepository(project_root=project_root)
            session_entity = session_repo.get(session_id)
            if session_entity:
                session = session_entity.to_dict()
                session_path = session_repo.get_session_json_path(session_id)
                if session_path and "parent" not in session:
                    session = dict(session)
                    session["parent"] = str(session_path.parent)
        except Exception:
            # Session not found or error - continue with fallback
            pass

        def _add(path: Optional[Path]) -> None:
            """Add path to bases list if not already present."""
            if path is None:
                return
            resolved = path.resolve()
            if resolved not in bases:
                bases.append(resolved)

        # Add primary session base path
        primary = get_session_base_path(session, session_path=session_path)
        _add(primary)

        # Add variations to handle different layouts
        if primary.name == session_id:
            # Flat layout - add parent as well
            _add(primary.parent)
        else:
            # Nested layout - add session_id subdirectory
            _add(primary / session_id)

        # Add standard session directories
        for sess_dir in get_session_dirs().values():
            _add((sess_dir / session_id).resolve())

    else:
        # Discovery mode - find all sessions
        for sess_dir in get_session_dirs().values():
            if not sess_dir.exists():
                continue
            try:
                for child in sess_dir.iterdir():
                    if child.is_dir():
                        resolved = child.resolve()
                        if resolved not in bases:
                            bases.append(resolved)
            except Exception:
                # Permission error or other issue - skip this directory
                continue

    return bases


def resolve_session_record_path(
    record_id: str,
    session_id: str,
    state: str,
    record_type: str,
    project_root: Optional[Path] = None,
) -> Path:
    """Resolve path for a record within a session directory.

    This function determines where a record (task or QA) should be stored
    within a session's directory structure. It:
    1. Tries to find the session via SessionRepository
    2. Falls back to searching standard session directories
    3. Defaults to wip state if session not found

    Args:
        record_id: Record identifier (e.g., "T-001-qa" or "T-001")
        session_id: Session identifier
        state: Record state (e.g., "waiting", "todo", "wip", "done")
        record_type: Type of record ("qa" or "task")
        project_root: Optional project root (defaults to current project)

    Returns:
        Path where the record should be stored

    Examples:
        # Resolve QA record path
        path = resolve_session_record_path(
            record_id="T-001-qa",
            session_id="sess-123",
            state="waiting",
            record_type="qa"
        )
        # Returns: .project/sessions/wip/sess-123/qa/waiting/T-001-qa.md

        # Resolve task record path
        path = resolve_session_record_path(
            record_id="T-001",
            session_id="sess-123",
            state="todo",
            record_type="task"
        )
        # Returns: .project/sessions/wip/sess-123/tasks/todo/T-001.md
    """
    # Lazy import to avoid circular dependency
    from edison.core.task.paths import get_session_dirs

    project_root = project_root or PathResolver.resolve_project_root()
    session_base: Optional[Path] = None

    # 1. Try SessionRepository first (most reliable)
    try:
        from edison.core.session.persistence.repository import SessionRepository
        session_repo = SessionRepository(project_root=project_root)
        path = session_repo.get_session_json_path(session_id)
        if path:
            session_entity = session_repo.get(session_id)
            if session_entity:
                session = session_entity.to_dict()
                session_base = get_session_base_path(session, session_path=path)
    except Exception:
        # Session not found or error - continue with fallback
        pass

    # 2. If not found, search standard directories
    if not session_base:
        # Use config-driven session state directories
        for sess_dir in get_session_dirs().values():
            candidate = sess_dir / session_id
            if candidate.exists():
                session_base = candidate
                break

    # 3. Default to wip using config-driven path resolution
    if not session_base:
        # Use config-driven path resolution
        from edison.core.utils.paths import get_management_paths
        mgmt = get_management_paths(project_root)
        session_base = mgmt.get_session_state_dir("wip") / session_id

    # Ensure we target the specific session directory
    if session_base.name != session_id:
        session_base = session_base / session_id

    # Determine record directory name based on type
    record_dir = "qa" if record_type == "qa" else "tasks"

    # Determine file extension
    file_extension = ".md"

    # Construct final path
    return session_base / record_dir / state / f"{record_id}{file_extension}"


__all__ = [
    "get_session_bases",
    "resolve_session_record_path",
]
