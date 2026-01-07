"""High-level lock helpers for Edison workflows."""

from __future__ import annotations

from .evidence_capture import acquire_evidence_capture_lock
from .named import (
    LockEnabled,
    LockScope,
    NamedLockConfig,
    named_lock_path,
    parse_named_lock_config,
    resolve_lock_enabled,
    sanitize_lock_key,
)

__all__ = [
    "LockEnabled",
    "LockScope",
    "NamedLockConfig",
    "acquire_evidence_capture_lock",
    "named_lock_path",
    "parse_named_lock_config",
    "resolve_lock_enabled",
    "sanitize_lock_key",
]
