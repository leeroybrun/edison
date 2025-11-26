"""Shared utilities for session store operations."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from ...paths.resolver import PathResolver
from ..config import SessionConfig

# Initialize config once
_CONFIG = SessionConfig()


def reset_session_store_cache() -> None:
    """Reset the cached SessionConfig.

    This is primarily for testing purposes to ensure clean test state
    when environment variables or config files change.
    In production, this should rarely be needed.
    """
    global _CONFIG
    _CONFIG = SessionConfig()


def _sessions_root() -> Path:
    """Return the absolute sessions root directory path."""
    root = PathResolver.resolve_project_root()
    rel_path = _CONFIG.get_session_root_path()
    return (root / rel_path).resolve()


def _session_dir(state: str, session_id: str) -> Path:
    """Directory for a session in a given state."""
    # Map state to directory name via config
    state_map = _CONFIG.get_session_states()
    dir_name = state_map.get(state.lower(), state.lower())
    return _sessions_root() / dir_name / session_id


def _session_state_order(state: Optional[str] = None) -> List[str]:
    """Canonical lookup order for session states."""
    if state:
        return [str(state).lower()]
    # Prefer explicit lookup order from configuration; fall back to configured state keys.
    order = _CONFIG.get_session_lookup_order()
    if order:
        seq = [str(s).lower() for s in order]
    else:
        states = _CONFIG.get_session_states()
        seq = [k.lower() for k in states.keys()] if states else ["draft", "active", "done", "validated", "closing"]
    if "wip" not in seq:
        seq.append("wip")
    return seq


def sanitize_session_id(session_id: str) -> str:
    """Sanitize a user-supplied session identifier."""
    if not session_id:
        raise ValueError("Session ID cannot be empty")

    # Prevent path traversal
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise ValueError("Session ID contains path traversal or separators")

    # Config-driven validation
    regex = _CONFIG.get_id_regex()
    if not re.fullmatch(regex, session_id):
        raise ValueError("Session ID contains invalid characters")

    max_len = _CONFIG.get_max_id_length()
    if len(session_id) > max_len:
        raise ValueError(f"Session ID too long (max {max_len} chars)")

    return session_id


def normalize_session_id(session_id: str) -> str:
    """Public helper to normalize user-supplied session identifiers."""
    return sanitize_session_id(session_id)


def _session_filename(session_id: str) -> str:
    return f"{sanitize_session_id(session_id)}.json"


def _session_json_path(session_dir: Path) -> Path:
    """Return path to session.json within a session directory."""
    return session_dir / "session.json"


def _session_json_candidates(session_id: str, *, states: Optional[List[str]] = None) -> List[Path]:
    """Return candidate JSON paths for a session across layouts."""
    sid = sanitize_session_id(session_id)
    state_list = states or _session_state_order()
    root = _sessions_root()
    candidates: List[Path] = []
    state_map = _CONFIG.get_session_states()

    for s in state_list:
        s_norm = str(s).lower()
        dir_name = state_map.get(s_norm, s_norm)
        # New-style directory layout under .project/sessions/<state>/<sid>/session.json
        new_dir = root / dir_name / sid
        candidates.append(new_dir / "session.json")

    return candidates
