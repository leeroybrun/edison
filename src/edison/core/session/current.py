"""Current session tracking with worktree-awareness.

Resolution priority:
1. If in worktree: Read from .project/.session-id file
2. Fallback: auto_session_for_owner() (PID-based inference)

Persistence:
- Only persists in worktree mode (isolated directories)
- Non-worktree mode: no file storage (concurrent session safety)

This module provides a unified entry point for session ID resolution
that is aware of the execution context (worktree vs non-worktree).
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

    The file is stored in .project/.session-id within the worktree root.

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
    """Read session ID from file.
    
    Args:
        path: Path to the session ID file.
        
    Returns:
        Session ID string, or None if file is empty or unreadable.
    """
    try:
        content = path.read_text(encoding="utf-8").strip()
        if content:
            # Validate the stored session ID
            return validate_session_id(content)
        return None
    except (OSError, SessionIdError) as exc:
        logger.debug("Failed to read session ID file %s: %s", path, exc)
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


def _session_exists(session_id: str) -> bool:
    """Check if a session exists.

    Args:
        session_id: Session ID to check.

    Returns:
        True if the session exists.
    """
    try:
        from .persistence.repository import SessionRepository
        repo = SessionRepository()
        return repo.exists(session_id)
    except (FileNotFoundError, OSError) as e:
        logger.debug("Failed to check session existence for %s: %s", session_id, e)
        return False
    except ValueError as e:
        logger.warning("Invalid session ID %s: %s", session_id, e)
        return False


def _auto_session_for_owner() -> Optional[str]:
    """Get session ID using PID-based inference.

    Returns:
        Session ID from process tree inference, or None.
    """
    try:
        from .persistence.repository import SessionRepository
        from edison.core.utils.process import get_current_owner
        from edison.core.config.domains.session import SessionConfig
        
        repo = SessionRepository()
        owner = get_current_owner()
        sessions = repo.find_by_owner(owner)
        
        # Get active session state from config (lookup order indicates priority)
        session_cfg = SessionConfig()
        lookup_order = session_cfg.get_session_lookup_order()
        # First state in lookup order is typically the active "wip" state
        active_state = lookup_order[0] if lookup_order else "wip"
        
        # Return first session in active state
        for sess in sessions:
            if sess.state == active_state:
                return sess.id
        return None
    except (FileNotFoundError, OSError) as e:
        logger.debug("Failed to infer session from process tree: %s", e)
        return None
    except ValueError as e:
        logger.warning("Invalid session data during inference: %s", e)
        return None


def get_current_session() -> Optional[str]:
    """Get current session ID with worktree-aware resolution.
    
    Resolution priority:
    1. If in worktree: Read from .project/.session-id file (if exists and valid)
    2. Fallback: auto_session_for_owner() (PID-based inference from process tree)
    
    In worktree mode, the file enables crash recovery and session resume.
    In non-worktree mode, only PID-based inference is used (safe for concurrent sessions).
    
    Returns:
        Current session ID, or None if unable to determine.
        
    Example:
        >>> session_id = get_current_session()
        >>> if session_id:
        ...     print(f"Current session: {session_id}")
        ... else:
        ...     print("No current session found")
    """
    # 1. Check if we're in a worktree - try file-based resolution first
    if _is_in_worktree():
        session_id_file = _get_session_id_file()
        if session_id_file and session_id_file.exists():
            stored_id = _read_session_id_file(session_id_file)
            if stored_id:
                # Validate the stored session still exists
                if _session_exists(stored_id):
                    logger.debug("Using stored session ID from file: %s", stored_id)
                    return stored_id
                else:
                    logger.debug(
                        "Stored session ID %s no longer exists, falling back to inference",
                        stored_id,
                    )
    
    # 2. Fallback to process-based inference
    inferred_id = _auto_session_for_owner()
    if inferred_id:
        logger.debug("Using inferred session ID from process tree: %s", inferred_id)
    return inferred_id


def set_current_session(session_id: str) -> None:
    """Set current session ID (worktree mode only).
    
    In worktree mode, persists the session ID to .project/.session-id file.
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
            "In non-worktree mode, session ID is inferred from the process tree. "
            "Use worktrees for persistent session tracking, or pass --session explicitly.",
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
    
    Removes the .project/.session-id file in worktree mode.
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
