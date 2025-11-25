"""
Session domain package for Edison core.

This package provides a focused public surface for session lifecycle
operations, state machine helpers and related data models. Legacy
callers should prefer importing from this package instead of the
monolithic :mod:`lib.sessionlib` module.
"""
from __future__ import annotations

from .manager import (
    SessionManager,
    create_session,
    get_session,
    list_sessions,
    transition_session,
)
from . import state as _state  # noqa: F401
from . import validation as _validation  # noqa: F401
from . import models as _models  # noqa: F401

__all__ = [
    "SessionManager",
    "state",
    "validation",
    "models",
]

# Re-export submodules under predictable names
state = _state
validation = _validation
models = _models
