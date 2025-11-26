"""Test helper functions for session operations.

This module provides convenience functions for tests. It delegates to the
canonical edison.core.session.store module (DRY principle).

Note: These are thin wrappers around production code for test convenience.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from edison.core.session import store as session_store
from edison.core.session import database as session_database
from edison.core.config.domains.project import get_project_name


# Re-export from canonical store module
ensure_session = session_store.ensure_session
load_session = session_store.load_session
transition_state = session_store.transition_state
_get_worktree_base = session_store._get_worktree_base


def _get_project_name() -> str:
    name = get_project_name()
    if not name:
        raise ValueError("PROJECT_NAME is required")
    return name


def _get_database_url() -> str:
    return session_database._get_database_url()


def close_session(session_id: str) -> Path:
    """Close a session (transition to closing state)."""
    session_store.transition_state(session_id, "closing")
    return session_store.get_session_json_path(session_id).parent


def validate_session(session_id: str) -> Path:
    """Validate a session (transition to validated state)."""
    session_store.transition_state(session_id, "validated")
    return session_store.get_session_json_path(session_id).parent


def get_session_state(session_dir: Path) -> str:
    """Get the current state of a session from its directory."""
    json_path = Path(session_dir) / "session.json"
    if not json_path.exists():
        raise ValueError("session.json missing")
    text = json_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid session.json") from exc
    if "state" not in data:
        raise ValueError("session state missing")
    return str(data["state"])


def handle_timeout(session_dir: Path) -> Path:
    """Move a session to recovery state on timeout."""
    sess_dir = Path(session_dir).resolve()
    sid = sess_dir.name
    session_store.transition_state(sid, "recovery", reason="timeout")
    return session_store.get_session_json_path(sid).parent
