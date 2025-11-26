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

from . import _shared
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

    # T-016 Analysis: This is NOT a legacy fallback - it's legitimate runtime robustness
    #
    # Purpose: Graceful recovery when lookupOrder config is incomplete or customized
    #
    # Example scenario:
    #   - User customizes lookupOrder: ["draft", "done"] (omits "active")
    #   - Session exists at .project/sessions/active/my-session/session.json
    #   - Primary search (lines 154-174) misses it (only checks draft/ and done/)
    #   - This fallback finds it by searching active/ directory
    #
    # Why it's LEGITIMATE (not legacy):
    #   1. Searches SAME file format (session.json), not deprecated files
    #   2. Config-driven (active_dirname from get_session_states())
    #   3. Runtime discovery robustness, not build-time backward compatibility
    #   4. No better alternative (strict validation = sessions become invisible on config error)
    #   5. Active use case: sessions CAN be in "active" state
    #
    # Differs from removed patterns (T-016):
    #   - Pattern 1 (REMOVED): ORCHESTRATOR_GUIDE.md fallback (deprecated file format)
    #   - Pattern 2A (REMOVED): safe_include() shim (legacy syntax conversion)
    #   - Pattern 3 (REMOVED): Hardcoded workflow defaults (NO HARDCODED VALUES principle)
    #   - Pattern 4 (THIS - KEPT): Session discovery (same format, alternate location)
    #
    # Fallback: search by directory name under active sessions when lookup order misses it
    active_dirname = _shared._CONFIG.get_session_states().get("active", "active")
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
    # If session exists, use its current path. If not, default to Wip/new-layout
    try:
        j = get_session_json_path(sid)
    except SessionNotFoundError:
        # Create new in initial state using configured layout
        initial_state = _shared._CONFIG.get_initial_session_state()
        j = _session_dir(initial_state, sid) / "session.json"

    ensure_directory(j.parent)
    with acquire_file_lock(j, timeout=5):
        _write_json(j, data)


def _ensure_session_dirs() -> None:
    states = _shared._CONFIG.get_session_states()
    for dirname in states.values():
        ensure_directory(_sessions_root() / dirname)
    ensure_directory(_sessions_root() / "wip")


def _read_template() -> Dict[str, Any]:
    """Load the session template JSON."""
    # Config-driven template paths
    primary_path = Path(_shared._CONFIG.get_template_path("primary"))
    repo_path = Path(_shared._CONFIG.get_template_path("repo"))

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
        initial_state = _shared._CONFIG.get_initial_session_state()
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
