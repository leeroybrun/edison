"""Shared utilities for session store operations."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from .._config import get_config, reset_config_cache
from ..id import validate_session_id, validate_session_id

if TYPE_CHECKING:
    from ...utils.paths.resolver import PathResolver

# Re-export for backward compatibility
validate_session_id = validate_session_id


def reset_session_store_cache() -> None:
    """Reset the cached SessionConfig.

    This is primarily for testing purposes to ensure clean test state
    when environment variables or config files change.
    In production, this should rarely be needed.
    """
    reset_config_cache()


def _sessions_root() -> Path:
    """Return the absolute sessions root directory path."""
    # Lazy import to avoid circular dependency
    from ...utils.paths.resolver import PathResolver
    root = PathResolver.resolve_project_root()
    rel_path = get_config().get_session_root_path()
    return (root / rel_path).resolve()


def _session_dir(state: str, session_id: str) -> Path:
    """Directory for a session in a given state."""
    # Map state to directory name via config
    state_map = get_config().get_session_states()
    dir_name = state_map.get(state.lower(), state.lower())
    return _sessions_root() / dir_name / session_id


def _session_state_order(state: Optional[str] = None) -> List[str]:
    """Canonical lookup order for session states."""
    if state:
        return [str(state).lower()]
    # Prefer explicit lookup order from configuration; fall back to configured state keys.
    config = get_config()
    order = config.get_session_lookup_order()
    if order:
        seq = [str(s).lower() for s in order]
    else:
        states = config.get_session_states()
        seq = [k.lower() for k in states.keys()] if states else ["draft", "active", "done", "validated", "closing"]
    if "wip" not in seq:
        seq.append("wip")
    return seq


def _session_filename(session_id: str) -> str:
    return f"{validate_session_id(session_id)}.json"


def _session_json_path(session_dir: Path) -> Path:
    """Return path to session.json within a session directory."""
    return session_dir / "session.json"


def _session_json_candidates(session_id: str, *, states: Optional[List[str]] = None) -> List[Path]:
    """Return candidate JSON paths for a session across layouts."""
    sid = validate_session_id(session_id)
    state_list = states or _session_state_order()
    root = _sessions_root()
    candidates: List[Path] = []
    state_map = get_config().get_session_states()

    for s in state_list:
        s_norm = str(s).lower()
        dir_name = state_map.get(s_norm, s_norm)
        # New-style directory layout under .project/sessions/<state>/<sid>/session.json
        new_dir = root / dir_name / sid
        candidates.append(new_dir / "session.json")

    return candidates
