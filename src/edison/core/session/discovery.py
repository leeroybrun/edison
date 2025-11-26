"""Session discovery utilities - find session.json files.

This module provides utilities to locate session.json files using:
- Hierarchical layout: {sessions_root}/{state}/{session_id}/session.json

All configuration (states, state mappings) comes from SessionConfig.
NO HARDCODED VALUES.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING

from .config import SessionConfig

if TYPE_CHECKING:
    # Avoid circular import at runtime
    from typing import Callable

logger = logging.getLogger(__name__)


def _get_sanitize_session_id() -> "Callable[[str], str]":
    """Lazy import of sanitize_session_id to avoid circular dependency."""
    from .store import sanitize_session_id
    return sanitize_session_id


def find_session_json_candidates(
    session_id: str,
    sessions_root: Path,
    states: Optional[List[str]] = None,
    state_map: Optional[Dict[str, str]] = None,
) -> List[Path]:
    """Find all possible session.json paths for a session ID.

    Searches using the hierarchical layout:
    - {sessions_root}/{state}/{session_id}/session.json

    Args:
        session_id: The session identifier (will be sanitized)
        sessions_root: Root directory containing session state directories
        states: Optional list of states to search (defaults to config lookup order)
        state_map: Optional mapping of state names to directory names (defaults to config)

    Returns:
        List of Path objects representing all candidate locations.
        Paths are returned in priority order based on state sequence.
        Note: Returned paths may or may not exist - call .exists() to check.

    Raises:
        ValueError: If session_id is invalid (via sanitize_session_id)

    Example:
        >>> candidates = find_session_json_candidates(
        ...     "my-session",
        ...     Path(".project/sessions"),
        ...     states=["wip", "done"]
        ... )
        >>> existing = [p for p in candidates if p.exists()]
    """
    # Validate session ID (lazy import to avoid circular dependency)
    sanitize_session_id = _get_sanitize_session_id()
    sid = sanitize_session_id(session_id)

    # Get configuration
    config = SessionConfig()

    # Use provided states or fall back to configured lookup order
    if states is None:
        # Get lookup order from config
        lookup_order = config.get_session_lookup_order()
        state_list = [str(s).lower() for s in lookup_order]
    else:
        state_list = [str(s).lower() for s in states]

    # Use provided state map or fall back to configured states
    if state_map is None:
        state_map = config.get_session_states()

    candidates: List[Path] = []

    for state in state_list:
        # Map state name to directory name
        dir_name = state_map.get(state, state)

        # New-style directory layout: {root}/{state_dir}/{sid}/session.json
        new_layout_dir = sessions_root / dir_name / sid
        candidates.append(new_layout_dir / "session.json")

    return candidates


def resolve_session_json(
    session_id: str,
    sessions_root: Path,
    states: Optional[List[str]] = None,
) -> Optional[Path]:
    """Find the actual session.json file, returning first that exists.

    This is the primary discovery function - it returns the first existing
    session.json file from the candidate list.

    Args:
        session_id: The session identifier (will be sanitized)
        sessions_root: Root directory containing session state directories
        states: Optional list of states to search (defaults to config lookup order)

    Returns:
        Path to session.json if found, None otherwise.

    Raises:
        ValueError: If session_id is invalid (via sanitize_session_id)

    Example:
        >>> path = resolve_session_json("my-session", Path(".project/sessions"))
        >>> if path:
        ...     from edison.core.file_io.utils import read_json_safe
        ...     data = read_json_safe(path)
    """
    candidates = find_session_json_candidates(
        session_id=session_id,
        sessions_root=sessions_root,
        states=states,
    )

    # Return first existing path
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


__all__ = [
    "find_session_json_candidates",
    "resolve_session_json",
]
