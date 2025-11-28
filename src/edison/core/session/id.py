"""Unified session ID validation, sanitization, and detection.

This module provides a single source of truth for session ID validation
and detection, eliminating duplicate implementations across the codebase.

All session ID validation and detection should go through this module.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from ._config import get_config


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
) -> Optional[str]:
    """Canonical session ID detection with validation.

    Detection priority:
    1. Explicit session ID parameter (if provided)
    2. project_SESSION environment variable (canonical)
    3. Auto-detect from owner / project_OWNER

    Auto-detection from owner looks for sessions in
    ``.project/sessions/active/`` whose ``session.json`` contains
    a matching ``owner`` field.

    Args:
        explicit: Explicit session ID if provided by caller
        owner: Owner name for auto-detection

    Returns:
        str: Normalized session ID, or None if cannot detect

    Raises:
        SessionIdError: If session ID format is invalid
    """
    # Priority 1: Explicit parameter
    if explicit:
        return validate_session_id(explicit)

    # Priority 2: project_SESSION environment variable (canonical)
    project_session = os.environ.get("project_SESSION")
    if project_session:
        return validate_session_id(project_session)

    # Priority 3: Auto-detect from owner / project_OWNER
    if owner is None:
        owner = os.environ.get("project_OWNER")

    if owner:
        try:
            # Lazy imports to avoid circular dependencies
            from edison.core.utils.io import read_json
            from edison.core.utils.paths import get_management_paths, resolve_project_root

            root = resolve_project_root()
            mgmt_paths = get_management_paths(root)
            sessions_active = mgmt_paths.get_session_state_dir("active")

            if not sessions_active.exists():
                return None

            # Look for session directories with matching owner
            for session_dir in sessions_active.iterdir():
                if not session_dir.is_dir():
                    continue

                session_json = session_dir / "session.json"
                if not session_json.exists():
                    continue

                try:
                    data = read_json(session_json)
                    if isinstance(data, dict) and data.get("owner") == owner:
                        return validate_session_id(session_dir.name)
                except Exception:
                    continue
        except Exception:
            pass

    return None


__all__ = [
    "SessionIdError",
    "validate_session_id",
    "detect_session_id",
]
