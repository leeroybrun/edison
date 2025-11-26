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
)

# Centralized configuration
from ._config import get_config, reset_config_cache

# Session ID validation
from .id import validate_session_id, sanitize_session_id, normalize_session_id, SessionIdError

# Submodules
from . import state as _state  # noqa: F401
from . import validation as _validation  # noqa: F401
from . import models as _models  # noqa: F401
from . import store as _store  # noqa: F401

__all__ = [
    # Manager
    "SessionManager",
    "create_session",
    "get_session",
    "list_sessions",
    "transition_session",
    # Config
    "get_config",
    "reset_config_cache",
    # ID validation
    "validate_session_id",
    "sanitize_session_id",
    "normalize_session_id",
    "SessionIdError",
    # Submodules
    "state",
    "validation",
    "models",
    "store",
]

# Re-export submodules under predictable names
state = _state
validation = _validation
models = _models
store = _store
