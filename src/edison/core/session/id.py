"""Unified session ID validation and sanitization.

This module provides a single source of truth for session ID validation,
eliminating duplicate implementations across the codebase.

All session ID validation should go through this module.
"""
from __future__ import annotations

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
            session_id
        )
    
    # Config-driven validation
    config = get_config()
    
    # Check max length first (before regex, as regex might be expensive)
    max_len = config.get_max_id_length()
    if len(session_id) > max_len:
        raise SessionIdError(
            f"Session ID too long: {len(session_id)} characters (max {max_len})",
            session_id
        )
    
    # Check regex pattern
    regex = config.get_id_regex()
    if not re.fullmatch(regex, session_id):
        raise SessionIdError(
            f"Session ID contains invalid characters: {session_id}. "
            f"Must match pattern: {regex}",
            session_id
        )
    
    return session_id


# Aliases for backward compatibility during migration
sanitize_session_id = validate_session_id
normalize_session_id = validate_session_id


__all__ = [
    "SessionIdError",
    "validate_session_id",
    "sanitize_session_id",
    "normalize_session_id",
]
