"""Session discovery and lookup operations."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ...legacy_guard import enforce_no_legacy_project_root
from ...exceptions import SessionNotFoundError

from .._config import get_config
from ._shared import (
    _session_json_candidates,
    _sessions_root,
    _session_state_order,
    sanitize_session_id,
    _session_dir,
)

# Fail-fast if running against a legacy (pre-Edison) project root
enforce_no_legacy_project_root("lib.session.store.discovery")


def get_session_json_path(session_id: str) -> Path:
    """Public helper: resolve the current ``session.json`` for ``session_id``."""
    sid = sanitize_session_id(session_id)
    # Prefer any existing JSON path across supported layouts.
    for path in _session_json_candidates(sid):
        if path.exists():
            return path
    # Fall back to raising via the existing error type for callers.
    raise SessionNotFoundError(
        f"session.json not found for {sid}",
        context={"sessionId": sid, "statesTried": _session_state_order()},
    )


def session_exists(session_id: str) -> bool:
    sid = sanitize_session_id(session_id)
    for path in _session_json_candidates(sid):
        if path.exists():
            return True
    return False


def _list_active_sessions() -> List[str]:
    try:
        active_dirname = get_config().get_session_states().get("active", "active")
        root = _sessions_root() / active_dirname
        if not root.exists():
            return []
        out: List[str] = []
        # Check for new layout (directories)
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "session.json").exists():
                out.append(d.name)
        return sorted(set(out))
    except Exception:
        return []


def auto_session_for_owner(owner: Optional[str]) -> Optional[str]:
    """
    Infer active session ID from process tree.

    This is the primary way Edison commands discover their session ID.

    Priority:
      1. PID-based inference from process tree
      2. Owner-based lookup (fallback)

    Args:
        owner: Optional owner name (used for fallback only)

    Returns:
        PID-based session ID (e.g., "edison-pid-12345") or owner-based session ID
    """
    # Try PID-based inference first
    session_id: Optional[str] = None
    try:
        from ..process.inspector import infer_session_id
        session_id = infer_session_id()

        # Check if PID-based session exists
        if session_exists(session_id):
            return session_id
    except Exception:
        # If process inspection fails, fall through to owner-based lookup
        pass

    # Fallback: Owner-based lookup
    if owner:
        candidate = sanitize_session_id(owner)
        if session_exists(candidate):
            return candidate

    # Return the inferred PID-based session ID even if it doesn't exist yet.
    # This allows callers to use it for new session creation.
    if session_id:
        return session_id

    return None
