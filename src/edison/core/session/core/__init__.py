"""Core session models and utilities."""
from __future__ import annotations

from .models import (
    SessionPaths,
    TaskEntry,
    QAEntry,
    GitInfo,
    Session,
)
from .id import (
    SessionIdError,
    validate_session_id,
    detect_session_id,
)
from .naming import (
    SessionNamingError,
    reset_session_naming_counter,
    generate_session_id,
)
from .layout import (
    detect_layout,
    get_session_base_path,
)
from .context import SessionContext

__all__ = [
    # Models
    "SessionPaths",
    "TaskEntry",
    "QAEntry",
    "GitInfo",
    "Session",
    # ID validation
    "SessionIdError",
    "validate_session_id",
    "detect_session_id",
    # Naming
    "SessionNamingError",
    "reset_session_naming_counter",
    "generate_session_id",
    # Layout
    "detect_layout",
    "get_session_base_path",
    # Context
    "SessionContext",
]
