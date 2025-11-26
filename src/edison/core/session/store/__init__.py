"""Session storage and I/O operations."""
from __future__ import annotations

from ...legacy_guard import enforce_no_legacy_project_root

# Fail-fast if running against a legacy (pre-Edison) project root
enforce_no_legacy_project_root("lib.session.store")

# Re-export exceptions used by store modules
from ...exceptions import SessionNotFoundError, SessionStateError

# Export config accessor from centralized location
from .._config import get_config, reset_config_cache

# Export session ID validation from unified module
from ..id import validate_session_id, sanitize_session_id, normalize_session_id

# Export shared utilities
from ._shared import (
    reset_session_store_cache,
    _session_filename,
    _session_json_path,
    _sessions_root,
    _session_dir,
    _session_json_candidates,
    _session_state_order,
)

# Export persistence functions
from .persistence import (
    load_session,
    save_session,
    _read_json,
    _write_json,
    _ensure_session_dirs,
    _read_template,
    _load_or_create_session,
)

# Export discovery functions
from .discovery import (
    get_session_json_path,
    session_exists,
    auto_session_for_owner,
    _list_active_sessions,
)

# Export lifecycle functions
from .lifecycle import (
    ensure_session,
    transition_state,
    acquire_session_lock,
    render_markdown,
    _move_session_json_to,
    _append_state_history,
    _get_worktree_base,
)

__all__ = [
    # Public API - Core functions
    "load_session",
    "save_session",
    "session_exists",
    "get_session_json_path",
    "auto_session_for_owner",
    "ensure_session",
    "transition_state",
    "acquire_session_lock",
    "render_markdown",
    # Public API - Configuration and utilities
    "get_config",
    "reset_config_cache",
    "reset_session_store_cache",
    "validate_session_id",
    "sanitize_session_id",
    "normalize_session_id",
    # Public API - Exceptions
    "SessionNotFoundError",
    "SessionStateError",
    # Internal functions (prefixed with _ but still exported for compatibility)
    "_session_filename",
    "_session_json_path",
    "_sessions_root",
    "_session_dir",
    "_session_json_candidates",
    "_session_state_order",
    "_ensure_session_dirs",
    "_read_template",
    "_load_or_create_session",
    "_list_active_sessions",
    "_move_session_json_to",
    "_append_state_history",
    "_get_worktree_base",
    "_read_json",
    "_write_json",
]
