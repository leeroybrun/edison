"""Current session tracking with worktree-aware persistence.

Session ID resolution is delegated to the canonical resolver
`edison.core.session.core.id.detect_session_id`, which uses this priority:
1. `AGENTS_SESSION` environment variable (must exist)
2. Worktree `<project-management-dir>/.session-id` file (must exist)
3. Process-derived `{process}-pid-{pid}` lookup (must exist)
4. Owner-based active session lookup (best-effort)

Persistence:
- Only persists in worktree mode via `<project-management-dir>/.session-id`
- Non-worktree mode: no file storage (safe for concurrent sessions)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..exceptions import SessionError
from .core.id import validate_session_id, SessionIdError

logger = logging.getLogger(__name__)

# File name for storing current session ID in worktree mode
_SESSION_ID_FILENAME = ".session-id"


def _is_in_worktree() -> bool:
    """Check if current directory is inside a git worktree.

    Returns:
        True if in a linked worktree (not the primary checkout).
    """
    try:
        from edison.core.utils.git.worktree import is_worktree
        return is_worktree()
    except (OSError, RuntimeError) as e:
        logger.debug("Failed to check worktree status: %s", e)
        return False


def _get_session_id_file() -> Optional[Path]:
    """Get path to .session-id file if in worktree.

    The file is stored in <project-management-dir>/.session-id within the worktree root.

    Returns:
        Path to the session ID file, or None if not in worktree.
    """
    if not _is_in_worktree():
        return None

    try:
        from edison.core.utils.paths import PathResolver, get_management_paths
        project_root = PathResolver.resolve_project_root()
        mgmt = get_management_paths(project_root)
        return mgmt.get_management_root() / _SESSION_ID_FILENAME
    except (FileNotFoundError, OSError, RuntimeError) as e:
        logger.debug("Failed to resolve session ID file path: %s", e)
        return None


def _read_session_id_file(path: Path) -> Optional[str]:
    """Deprecated internal helper (kept for backward compatibility in tests)."""
    try:
        content = path.read_text(encoding="utf-8").strip()
        return validate_session_id(content) if content else None
    except (OSError, SessionIdError):
        return None


def _write_session_id_file(path: Path, session_id: str) -> None:
    """Write session ID to file.
    
    Args:
        path: Path to the session ID file.
        session_id: Session ID to write.
        
    Raises:
        SessionError: If unable to write file.
    """
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(session_id + "\n", encoding="utf-8")
        logger.debug("Wrote session ID %s to %s", session_id, path)
    except OSError as exc:
        raise SessionError(
            f"Failed to write session ID file: {exc}",
            context={"path": str(path), "session_id": session_id},
        ) from exc


def _delete_session_id_file(path: Path) -> None:
    """Delete session ID file.
    
    Args:
        path: Path to the session ID file.
    """
    try:
        if path.exists():
            path.unlink()
            logger.debug("Deleted session ID file %s", path)
    except OSError as exc:
        logger.warning("Failed to delete session ID file %s: %s", path, exc)


def get_current_session() -> Optional[str]:
    """Get current session ID with worktree-aware resolution.
    
    Resolution priority:
    1. AGENTS_SESSION environment variable (canonical)
    2. Worktree `<project-management-dir>/.session-id` file (if exists and valid)
    3. Process-derived `{process}-pid-{pid}` lookup (if exists)
    
    In worktree mode, the file enables crash recovery and session resume.
    In non-worktree mode, no file storage is used (safe for concurrent sessions).
    
    Returns:
        Current session ID, or None if unable to determine.
        
    Example:
        >>> session_id = get_current_session()
        >>> if session_id:
        ...     print(f"Current session: {session_id}")
        ... else:
        ...     print("No current session found")
    """
    try:
        from edison.core.session.core.id import detect_session_id
        from edison.core.utils.paths import PathResolver

        root = PathResolver.resolve_project_root()
        # get_current_session() is intended to return an existing session for scoping.
        return detect_session_id(project_root=root)
    except Exception:
        return None


def set_current_session(session_id: str) -> None:
    """Set current session ID (worktree mode only).
    
    In worktree mode, persists the session ID to <project-management-dir>/.session-id file.
    This enables session resume after process crashes or restarts.
    
    In non-worktree mode, raises an error because file storage would be
    unsafe with multiple concurrent sessions in the same directory.
    
    Args:
        session_id: Session ID to set as current.
        
    Raises:
        SessionError: If not in worktree mode or validation fails.
        SessionIdError: If session ID format is invalid.
        
    Example:
        >>> set_current_session("claude-pid-12345")
    """
    # Validate format first
    session_id = validate_session_id(session_id)
    
    if not _is_in_worktree():
        raise SessionError(
            "Cannot set current session outside of a worktree. "
            "Outside worktrees, session scoping should use AGENTS_SESSION. "
            "Use worktrees for persistent session tracking, or pass --session explicitly.",
            context={"session_id": session_id},
        )

    # Fail closed: only allow setting a session that already exists in this project.
    # Sessions must be created via `edison session create` first.
    try:
        from edison.core.utils.paths import PathResolver
        from .persistence.repository import SessionRepository

        root = PathResolver.resolve_project_root()
        repo = SessionRepository(project_root=root)
        if not repo.exists(session_id):
            raise SessionError(
                f"Session not found: {session_id}",
                context={"session_id": session_id, "project_root": str(root)},
            )
    except SessionError:
        raise
    except Exception:
        # If project root / repository cannot be resolved, treat it as unsafe.
        raise SessionError(
            "Unable to verify session exists; refusing to set current session",
            context={"session_id": session_id},
        )
    
    session_id_file = _get_session_id_file()
    if session_id_file:
        _write_session_id_file(session_id_file, session_id)
        logger.info("Set current session to: %s", session_id)
    else:
        raise SessionError(
            "Unable to determine session ID file path",
            context={"session_id": session_id},
        )


def clear_current_session() -> None:
    """Clear current session ID (worktree mode only).
    
    Removes the <project-management-dir>/.session-id file in worktree mode.
    In non-worktree mode, this is a no-op (nothing to clear).
    
    Example:
        >>> clear_current_session()
    """
    if not _is_in_worktree():
        logger.debug("Not in worktree mode, nothing to clear")
        return
    
    session_id_file = _get_session_id_file()
    if session_id_file:
        _delete_session_id_file(session_id_file)
        logger.info("Cleared current session")


__all__ = [
    "get_current_session",
    "set_current_session",
    "clear_current_session",
]
