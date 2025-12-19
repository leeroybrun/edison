"""Unified session ID validation, sanitization, and detection.

This module provides a single source of truth for session ID validation
and detection, eliminating duplicate implementations across the codebase.

All session ID validation and detection should go through this module.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from .._config import get_config


class SessionIdError(ValueError):
    """Raised when session ID validation fails."""

    def __init__(self, message: str, session_id: Optional[str] = None):
        super().__init__(message)
        self.session_id = session_id


def validate_session_id(session_id: str) -> str:
    """Validate and sanitize a session ID.

    This is the single source of truth for session ID validation.

    Validation rules:
    - Cannot be empty
    - Cannot contain path traversal sequences (.., /, \\)
    - Must match the configured regex pattern
    - Cannot exceed the configured maximum length

    Args:
        session_id: The session ID to validate

    Returns:
        The validated session ID (unchanged if valid)

    Raises:
        SessionIdError: If validation fails

    Example:
        >>> validate_session_id("my-session-123")
        'my-session-123'
        >>> validate_session_id("")
        Traceback (most recent call last):
            ...
        SessionIdError: Session ID cannot be empty
    """
    if not session_id:
        raise SessionIdError("Session ID cannot be empty", session_id)

    # Prevent path traversal
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise SessionIdError(
            f"Session ID contains path traversal or separators: {session_id}",
            session_id,
        )

    # Config-driven validation
    config = get_config()

    # Check max length first (before regex, as regex might be expensive)
    max_len = config.get_max_id_length()
    if len(session_id) > max_len:
        raise SessionIdError(
            f"Session ID too long: {len(session_id)} characters (max {max_len})",
            session_id,
        )

    # Check regex pattern
    regex = config.get_id_regex()
    if not re.fullmatch(regex, session_id):
        raise SessionIdError(
            f"Session ID contains invalid characters: {session_id}. "
            f"Must match pattern: {regex}",
            session_id,
        )

    return session_id


def detect_session_id(
    explicit: Optional[str] = None,
    owner: Optional[str] = None,
    *,
    project_root: Optional[Path] = None,
) -> Optional[str]:
    """Canonical session ID detection with validation.

    Detection priority:
    1. Explicit session ID parameter (if provided)
    2. AGENTS_SESSION environment variable (canonical)
    3. Worktree `.project/.session-id` file (if present + valid + exists)
    4. Process-derived `{process}-pid-{pid}` lookup (if exists)
    5. Auto-detect from explicit owner / AGENTS_OWNER (if provided)

    Auto-detection uses SessionRepository as the single source of truth and
    prefers sessions in semantic "active" state (directory mapping is config-driven).

    Args:
        explicit: Explicit session ID if provided by caller
        owner: Owner name for auto-detection

    Returns:
        str: Normalized session ID, or None if cannot detect

    Raises:
        SessionIdError: If session ID format is invalid
    """
    from edison.core.utils.paths import resolve_project_root
    from edison.core.session.persistence.repository import SessionRepository

    root = Path(project_root).resolve() if project_root is not None else resolve_project_root()
    repo = SessionRepository(project_root=root)

    # Priority 1: Explicit parameter (must exist)
    if explicit:
        sid = validate_session_id(explicit)
        return sid if repo.exists(sid) else None

    # Priority 2: AGENTS_SESSION environment variable (canonical)
    env_session = os.environ.get("AGENTS_SESSION")
    if env_session:
        sid = validate_session_id(env_session)
        return sid if repo.exists(sid) else None

    # Priority 3: Worktree session file (exists+valid+points to existing session)
    try:
        from edison.core.utils.paths import get_management_paths

        mgmt = get_management_paths(root)
        session_file = (mgmt.get_management_root() / ".session-id").resolve()
        if session_file.exists():
            raw = session_file.read_text(encoding="utf-8").strip()
            if raw:
                sid = validate_session_id(raw)
                if repo.exists(sid):
                    return sid
    except (OSError, SessionIdError):
        # Fail closed by ignoring corrupted or unreadable session-id file.
        # Callers that require an explicit session must pass it (or set AGENTS_SESSION).
        pass

    # Priority 4: Process-derived lookup (exists only)
    try:
        from edison.core.utils.process.inspector import find_topmost_process

        process_name, pid = find_topmost_process()
        candidate = validate_session_id(f"{process_name}-pid-{pid}")
        if repo.exists(candidate):
            return candidate
    except Exception:
        pass

    # Priority 5: Auto-detect from owner / AGENTS_OWNER (best-effort)
    if owner is None:
        owner = os.environ.get("AGENTS_OWNER")

    if owner:
        try:
            from edison.core.config.domains.workflow import WorkflowConfig

            workflow = WorkflowConfig(repo_root=root)
            active_state = workflow.get_semantic_state("session", "active")

            candidates = [s for s in repo.find_by_owner(str(owner)) if str(s.state) == str(active_state)]
            if not candidates:
                return None

            def _last_active(sess) -> str:
                try:
                    return str(getattr(sess, "metadata").updated_at or "")
                except Exception:
                    return ""

            candidates.sort(key=_last_active, reverse=True)
            return validate_session_id(candidates[0].id)
        except Exception:
            return None

    return None


def require_session_id(
    explicit: Optional[str] = None,
    *,
    project_root: Optional[Path] = None,
) -> str:
    """Resolve a session id using canonical detection and require it to exist.

    This is the recommended entrypoint for CLIs and workflows that need a real
    session scope (claiming, session status, etc).
    """
    from edison.core.utils.paths import resolve_project_root
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.exceptions import SessionNotFoundError

    root = Path(project_root).resolve() if project_root is not None else resolve_project_root()
    repo = SessionRepository(project_root=root)

    # Explicit always wins and must exist.
    if explicit:
        sid = validate_session_id(explicit)
        if not repo.exists(sid):
            raise SessionNotFoundError(
                f"Session {sid} not found",
                context={"sessionId": sid, "projectRoot": str(root), "source": "explicit"},
            )
        return sid

    # AGENTS_SESSION is canonical and must exist.
    env_session = os.environ.get("AGENTS_SESSION")
    if env_session:
        sid = validate_session_id(env_session)
        if not repo.exists(sid):
            raise SessionNotFoundError(
                f"Session {sid} not found (from AGENTS_SESSION)",
                context={"sessionId": sid, "projectRoot": str(root), "source": "AGENTS_SESSION"},
            )
        return sid

    sid = detect_session_id(project_root=root)
    if not sid:
        raise SessionNotFoundError(
            "No session could be resolved. Set AGENTS_SESSION, create a worktree session (session me --set), "
            "or create a session via `edison session create`.",
            context={"projectRoot": str(root)},
        )
    # detect_session_id guarantees existence for all non-env sources, but keep a defensive check.
    if not repo.exists(sid):
        raise SessionNotFoundError(
            f"Session {sid} not found",
            context={"sessionId": sid, "projectRoot": str(root)},
        )
    return sid


__all__ = [
    "SessionIdError",
    "validate_session_id",
    "detect_session_id",
    "require_session_id",
]
