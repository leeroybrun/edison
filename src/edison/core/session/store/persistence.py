"""Session persistence and I/O operations."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ...legacy_guard import enforce_no_legacy_project_root
from ...file_io.locking import acquire_file_lock
from ...file_io.utils import (
    write_json_safe as io_atomic_write_json,
    read_json_safe as io_read_json_safe,
    ensure_directory,
)
from ...utils.time import utc_timestamp as io_utc_timestamp
from ...exceptions import SessionNotFoundError, SessionStateError
from ...paths.resolver import PathResolver

from .._config import get_config
from ._shared import (
    _session_json_candidates,
    _sessions_root,
    _session_state_order,
    sanitize_session_id,
    _session_dir,
)

logger = logging.getLogger(__name__)

# Fail-fast if running against a legacy (pre-Edison) project root
enforce_no_legacy_project_root("lib.session.store.persistence")


def _read_json(path: Path) -> Dict[str, Any]:
    return io_read_json_safe(path)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    io_atomic_write_json(path, data, acquire_lock=False)


def load_session(session_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Load the JSON metadata for a session."""
    sid = sanitize_session_id(session_id)
    states = _session_state_order(state)
    candidates = [p for p in _session_json_candidates(sid, states=states) if p.exists()]
    if candidates:
        # Prefer the most recently modified session JSON
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        try:
            data = _read_json(newest)
        except Exception as exc:  # pragma: no cover - surfaced in edge-case tests
            raise SessionStateError(f"Failed to read session JSON at {newest}: {exc}", context={"sessionId": sid}) from exc

        # Fail closed if any other existing candidate is malformed to avoid silently masking corruption
        for other in candidates:
            if other == newest:
                continue
            try:
                _read_json(other)
            except Exception as exc:
                raise SessionStateError(
                    f"Session JSON corrupted at {other}: {exc}",
                    context={"sessionId": sid}
                ) from exc
        return data

    # Fallback: search by directory name under active sessions when lookup order misses it
    # This is runtime discovery robustness (NOT legacy), searches same format in alternate location
    active_dirname = get_config().get_session_states().get("active", "active")
    active_root = _sessions_root() / active_dirname
    fallback_json = active_root / sid / "session.json"
    if fallback_json.exists():
        return _read_json(fallback_json)
    for json_path in active_root.glob("*/session.json"):
        if json_path.parent.name == sid:
            return _read_json(json_path)

    raise SessionNotFoundError(
        f"session.json not found for {sid}",
        context={"sessionId": sid, "statesTried": states},
    )


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    """Safely persist session JSON using locking and atomic write."""
    from .discovery import get_session_json_path

    sid = sanitize_session_id(session_id)
    # If session exists, use its current path. If not, default to initial state
    try:
        j = get_session_json_path(sid)
    except SessionNotFoundError:
        # Create new in initial state using configured layout
        initial_state = get_config().get_initial_session_state()
        j = _session_dir(initial_state, sid) / "session.json"

    ensure_directory(j.parent)
    with acquire_file_lock(j, timeout=5):
        _write_json(j, data)


def _ensure_session_dirs() -> None:
    states = get_config().get_session_states()
    for dirname in states.values():
        ensure_directory(_sessions_root() / dirname)
    ensure_directory(_sessions_root() / "wip")


def _read_template() -> Dict[str, Any]:
    """Load the session template JSON."""
    # Config-driven template paths
    config = get_config()
    primary_path = Path(config.get_template_path("primary"))
    repo_path = Path(config.get_template_path("repo"))

    candidates = []
    for candidate in (primary_path, repo_path):
        if not str(candidate):
            continue
        if candidate.is_absolute():
            candidates.append(candidate)
        else:
            candidates.append(PathResolver.resolve_project_root() / candidate)

    for candidate in candidates:
        if candidate.exists():
            return io_read_json_safe(candidate)

    raise RuntimeError("Missing session template (checked configured paths)")


def _load_or_create_session(session_id: str) -> Dict[str, Any]:
    """Load existing session JSON or create a minimal skeleton."""
    sid = sanitize_session_id(session_id)
    try:
        return load_session(sid)
    except Exception:
        # Minimal skeleton for new sessions (kept intentionally small)
        # Use new layout by default
        initial_state = get_config().get_initial_session_state()
        sess_dir = _session_dir(initial_state, sid)
        ensure_directory(sess_dir)
        path = sess_dir / "session.json"
        data: Dict[str, Any] = {
            "id": sid,
            "meta": {
                "sessionId": sid,
                "createdAt": io_utc_timestamp(),
                "lastActive": io_utc_timestamp(),
            },
            "tasks": {},
            "qa": {},
            "activityLog": [],
        }
        return data
