"""
Session domain package for Edison core.

This package provides a focused public surface for session lifecycle
operations, state machine helpers and related data models.
"""
from __future__ import annotations

# Core session management
from .manager import (
    SessionManager,
    create_session,
    get_session,
    list_sessions,
    transition_session,
    # Current session tracking (worktree-aware)
    get_current_session,
    set_current_session,
    clear_current_session,
)

# Centralized configuration
from ._config import get_config, reset_config_cache

# Session ID validation
from .id import validate_session_id, SessionIdError

# Repository (persistence layer)
from .repository import SessionRepository

# Path resolution utilities
from .paths import get_session_bases, resolve_session_record_path

__all__ = [
    # Manager
    "SessionManager",
    "create_session",
    "get_session",
    "list_sessions",
    "transition_session",
    # Current session tracking (worktree-aware)
    "get_current_session",
    "set_current_session",
    "clear_current_session",
    # Config
    "get_config",
    "reset_config_cache",
    # ID validation
    "validate_session_id",
    "SessionIdError",
    # Repository
    "SessionRepository",
    # Path resolution
    "get_session_bases",
    "resolve_session_record_path",
]
