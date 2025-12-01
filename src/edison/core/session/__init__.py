"""
Session domain package for Edison core.

This package provides a focused public surface for session lifecycle
operations, state machine helpers and related data models.
"""
from __future__ import annotations

# Core session management
from .lifecycle.manager import (
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
from .core.id import validate_session_id, SessionIdError

# Repository (persistence layer)
from .persistence.repository import SessionRepository
from .persistence import archive
from .persistence import database
from .persistence import graph

# Lifecycle submodules
from . import lifecycle
from .lifecycle import recovery
from .lifecycle import transaction
from .lifecycle import autostart

# Worktree submodule
from . import worktree

# Core submodules
from .core import id
from .core import models

# Next submodule
from . import next

# Path resolution utilities
from .paths import get_session_bases, resolve_session_record_path

# Session context (worktree environment management)
from .core.context import SessionContext

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
    # Repository & Persistence
    "SessionRepository",
    # Lifecycle submodules
    "lifecycle",
    "recovery",
    "transaction",
    "autostart",
    # Worktree
    "worktree",
    # Core submodules
    "id",
    "models",
    # Next
    "next",
    # Path resolution
    "get_session_bases",
    "resolve_session_record_path",
    # Session context
    "SessionContext",
]
