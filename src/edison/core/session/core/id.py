"""Unified session ID validation, sanitization, and detection.

This module provides a single source of truth for session ID validation
and detection, eliminating duplicate implementations across the codebase.

All session ID validation and detection should go through this module.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .._config import get_config

if TYPE_CHECKING:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository


class SessionIdError(ValueError):
    """Raised when session ID validation fails."""

    def __init__(self, message: str, session_id: str | None = None):
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
    explicit: str | None = None,
    owner: str | None = None,
    *,
    project_root: Path | None = None,
) -> str | None:
    """Canonical session ID detection with validation.

    Detection priority:
    1. Explicit session ID parameter (if provided)
    2. AGENTS_SESSION environment variable (canonical)
    3. Worktree `.project/.session-id` file (ONLY in linked worktrees, never primary checkout)
    4. Process-derived `{process}-pid-{pid}` lookup with suffix handling
    5. Auto-detect from explicit owner / AGENTS_OWNER (if provided)

    Auto-detection uses SessionRepository as the single source of truth and
    prefers sessions in semantic "active" state (directory mapping is config-driven).

    IMPORTANT (task 001-session-id-inference):
    - `.session-id` is ONLY consulted inside linked worktrees (never primary checkout)
    - Process-derived lookup handles -seq-N suffixes for session uniqueness
    - When multiple sessions match a prefix, prefer active state then most recent

    Args:
        explicit: Explicit session ID if provided by caller
        owner: Owner name for auto-detection

    Returns:
        str: Normalized session ID, or None if cannot detect

    Raises:
        SessionIdError: If session ID format is invalid
    """
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths import resolve_project_root

    root = Path(project_root).resolve() if project_root is not None else resolve_project_root()
    repo = SessionRepository(project_root=root)

    # Priority 1: Explicit parameter (validated only; existence is enforced by require_session_id)
    if explicit:
        return validate_session_id(explicit)

    # Priority 2: AGENTS_SESSION environment variable (canonical)
    #
    # Only treat it as a match when the session exists. This avoids stale
    # environment variables forcing detection to a non-existent session.
    env_session = os.environ.get("AGENTS_SESSION")
    if env_session:
        sid = validate_session_id(env_session)
        if repo.exists(sid):
            return sid

    # Priority 3: Worktree session file (ONLY in linked worktrees - never primary checkout)
    # This prevents session ID leakage between sessions when running from primary checkout
    try:
        from edison.core.utils.git.worktree import is_worktree
        from edison.core.utils.paths import get_management_paths

        # Gate .session-id resolution behind worktree check (task 001-session-id-inference)
        if is_worktree(root):
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

    # Priority 4: Process-derived lookup with suffix handling (task 001-session-id-inference)
    # Handles session IDs with -seq-N suffixes for uniqueness
    # When multiple sessions match a prefix, prefer active state then most recent
    try:
        from edison.core.utils.process.inspector import find_topmost_process

        process_name, pid = find_topmost_process()
        process_prefix = f"{process_name}-pid-{pid}"

        # Find ALL sessions matching the prefix (including exact match and suffixed)
        # and prefer active ones, then most recently updated
        candidates = _find_sessions_by_prefix(repo, process_prefix, root)
        if candidates:
            return candidates[0]
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

            owner_sessions: list[Session] = [
                s for s in repo.find_by_owner(str(owner)) if str(s.state) == str(active_state)
            ]
            if not owner_sessions:
                return None

            def _last_active(sess: Session) -> str:
                try:
                    return str(sess.metadata.updated_at or "")
                except Exception:
                    return ""

            owner_sessions.sort(key=_last_active, reverse=True)
            return validate_session_id(owner_sessions[0].id)
        except Exception:
            return None

    return None


def _find_sessions_by_prefix(
    repo: SessionRepository,
    prefix: str,
    root: Path,
) -> list[str]:
    """Find sessions matching a process prefix, preferring active state then most recent.

    This handles session IDs with -seq-N suffixes for uniqueness.
    For example, for prefix "claude-pid-12345", matches:
    - "claude-pid-12345" (exact)
    - "claude-pid-12345-seq-1"
    - "claude-pid-12345-seq-2"

    Returns sessions sorted by: active state first, then most recently updated.
    """
    try:
        from edison.core.config.domains.workflow import WorkflowConfig

        workflow = WorkflowConfig(repo_root=root)
        active_state = str(workflow.get_semantic_state("session", "active"))
    except Exception:
        active_state = "active"

    # Find all sessions and filter by prefix
    all_sessions = repo.get_all()
    matching: list[Session] = []

    for session in all_sessions:
        sid = session.id
        # Match exact prefix or prefix followed by -seq-
        if sid == prefix or sid.startswith(f"{prefix}-seq-"):
            matching.append(session)

    if not matching:
        return []

    # Sort: active sessions first, then by updated_at descending
    def sort_key(sess: Session) -> tuple[int, str]:
        is_active = 1 if str(sess.state) == active_state else 0
        try:
            updated = str(sess.metadata.updated_at or "")
        except Exception:
            updated = ""
        # Return (is_active, updated) with reverse=True
        # This puts active sessions (1) before inactive ones (0)
        # And within each group, sorts by updated_at descending
        return (is_active, updated)

    matching.sort(key=sort_key, reverse=True)
    return [validate_session_id(s.id) for s in matching]


def require_session_id(
    explicit: str | None = None,
    *,
    project_root: Path | None = None,
) -> str:
    """Resolve a session id using canonical detection and require it to exist.

    This is the recommended entrypoint for CLIs and workflows that need a real
    session scope (claiming, session status, etc).
    """
    from edison.core.exceptions import SessionNotFoundError
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.paths import resolve_project_root

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

    detected_sid = detect_session_id(project_root=root)
    if not detected_sid:
        raise SessionNotFoundError(
            "No session could be resolved. Set AGENTS_SESSION, create a worktree session (session me --set), "
            "or create a session via `edison session create`.",
            context={"projectRoot": str(root)},
        )
    # detect_session_id guarantees existence for all non-env sources, but keep a defensive check.
    if not repo.exists(detected_sid):
        raise SessionNotFoundError(
            f"Session {detected_sid} not found",
            context={"sessionId": detected_sid, "projectRoot": str(root)},
        )
    return detected_sid


__all__ = [
    "SessionIdError",
    "validate_session_id",
    "detect_session_id",
    "require_session_id",
]
