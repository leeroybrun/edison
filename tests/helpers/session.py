"""Test helper functions for session operations.

This module provides convenience functions for tests using the new
SessionRepository and SessionService APIs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union, Dict, Any

from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.lifecycle.manager import SessionManager
from edison.core.session.worktree.config_helpers import _get_worktree_base


def ensure_session(session_id: str, state: str = "active") -> Path:
    """Ensure a session exists, creating it if necessary."""
    repo = SessionRepository()
    return repo.ensure_session(session_id, state=state)


def load_session(session_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Load a session by ID."""
    repo = SessionRepository()
    session = repo.get(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    return session.to_dict()


def transition_state(session_id: str, to_state: str, reason: Optional[str] = None) -> Path:
    """Transition a session to a new state."""
    mgr = SessionManager()
    return mgr.transition_state(session_id, to_state)


def close_session(session_id: str) -> Path:
    """Close a session (transition to closing state)."""
    mgr = SessionManager()
    mgr.transition_state(session_id, "closing")
    repo = SessionRepository()
    return repo.get_session_json_path(session_id).parent


def validate_session(session_id: str) -> Path:
    """Validate a session (transition to validated state)."""
    mgr = SessionManager()
    mgr.transition_state(session_id, "validated")
    repo = SessionRepository()
    return repo.get_session_json_path(session_id).parent


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
    mgr = SessionManager()
    mgr.transition_state(sid, "recovery")
    repo = SessionRepository()
    return repo.get_session_json_path(sid).parent
