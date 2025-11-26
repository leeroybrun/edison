"""Session storage and I/O operations."""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator, Union
from contextlib import contextmanager
from datetime import datetime, timezone

from ..paths.resolver import PathResolver
from ..legacy_guard import enforce_no_legacy_project_root
from .. import task
from ..file_io.locking import acquire_file_lock
from ..file_io.utils import (
    write_json_safe as io_atomic_write_json,
    read_json_safe as io_read_json_safe,
    utc_timestamp as io_utc_timestamp,
)
from ..exceptions import SessionNotFoundError, SessionStateError

logger = logging.getLogger(__name__)

# Constants
# Constants
# DATA_ROOT and REPO_DIR removed to ensure dynamic resolution via PathResolver/Config

from .config import SessionConfig

# Fail-fast if running against a legacy (pre-Edison) project root
enforce_no_legacy_project_root("lib.session.store")

# Initialize config once (or per call if dynamic reload needed, but once is usually fine for core lib)
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
    active_dirname = _CONFIG.get_session_states().get("active", "active")
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
    sid = sanitize_session_id(session_id)
    # If session exists, use its current path. If not, default to Wip/new-layout
    try:
        j = get_session_json_path(sid)
    except SessionNotFoundError:
        # Create new in initial state using configured layout
        initial_state = _CONFIG.get_initial_session_state()
        j = _session_dir(initial_state, sid) / "session.json"
    
    j.parent.mkdir(parents=True, exist_ok=True)
    with acquire_file_lock(j, timeout=5):
        _write_json(j, data)

def _ensure_session_dirs() -> None:
    states = _CONFIG.get_session_states()
    for dirname in states.values():
        (_sessions_root() / dirname).mkdir(parents=True, exist_ok=True)
    (_sessions_root() / "wip").mkdir(parents=True, exist_ok=True)

def _read_template() -> Dict[str, Any]:
    """Load the session template JSON."""
    # Config-driven template paths
    primary_path = Path(_CONFIG.get_template_path("primary"))
    repo_path = Path(_CONFIG.get_template_path("repo"))

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
        initial_state = _CONFIG.get_initial_session_state()
        sess_dir = _session_dir(initial_state, sid)
        sess_dir.mkdir(parents=True, exist_ok=True)
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

def _list_active_sessions() -> List[str]:
    try:
        root = _sessions_root() / "active"
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

def _move_session_json_to(status: str, session_id: str) -> Path:
    """Move session JSON to a new lifecycle directory using task.safe_move_file."""
    sid = sanitize_session_id(session_id)
    try:
        src = get_session_json_path(sid)
    except SessionNotFoundError:
        raise FileNotFoundError(f"Session {sid} not found")

    # Determine destination path (always use new layout for moves)
    dest_dir = _session_dir(status, sid)
    dest = dest_dir / "session.json"
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # If src is a directory (new layout), move the whole directory?
        # The original code moved the JSON file. But if we have a directory layout, we should move the directory.
        # However, the original code:
        # src = task.SESSION_DIRS["active"] / _session_filename(session_id)
        # dest = task.SESSION_DIRS[status] / _session_filename(session_id)
        # task.safe_move_file(src, dest)
        
        # If we are in new layout, src is .../sid/session.json.
        # We should probably move the parent directory if it matches sid.
        
        # It's a directory layout. Move the directory.
        import shutil
        # We need to move src.parent to dest_dir.parent (which is the status dir)
        # dest_dir is already correctly mapped via _session_dir(status, sid)
        # So we want to move src.parent (.../old_status/sid) to dest_dir

        if dest_dir.exists():
            shutil.rmtree(dest_dir) # Overwrite if exists

        shutil.move(str(src.parent), str(dest_dir))

        return dest / "session.json"

    except Exception as e:
        logger.error("Failed to move session JSON for %s to %s: %s", session_id, status, e)
        raise

def auto_session_for_owner(owner: Optional[str]) -> Optional[str]:
    """
    Infer active session ID from process tree.

    This is the primary way Edison commands discover their session ID.

    Priority:
      1. PID-based inference from process tree (NEW)
      2. Legacy owner-based lookup (FALLBACK for backward compatibility)

    Args:
        owner: Optional owner name (used for legacy fallback only)

    Returns:
        PID-based session ID (e.g., "edison-pid-12345") or legacy session ID

    Examples:
        # Auto-start workflow (Edison → Claude)
        auto_session_for_owner("claude")
        → Returns "edison-pid-12345" (Edison is topmost)

        # Manual workflow (Claude → Edison)
        auto_session_for_owner("claude")
        → Returns "claude-pid-54321" (Claude is topmost)

        # Legacy session still works
        auto_session_for_owner("old-session-name")
        → Returns "old-session-name" if it exists
    """
    # Try PID-based inference first (NEW behavior)
    session_id: Optional[str] = None
    try:
        from ..process.inspector import infer_session_id
        session_id = infer_session_id()

        # Check if PID-based session exists
        if session_exists(session_id):
            return session_id
    except Exception:
        # If process inspection fails, fall through to legacy behavior
        pass

    # Fallback: Legacy owner-based lookup (BACKWARD COMPATIBILITY)
    if owner:
        candidate = sanitize_session_id(owner)
        if session_exists(candidate):
            return candidate

    # Return the inferred PID-based session ID even if it doesn't exist yet.
    # This allows callers to use it for new session creation.
    if session_id:
        return session_id

    return None

@contextmanager
def acquire_session_lock(session_id: str, *, timeout: float = 5.0) -> Iterator[Path]:
    """Context manager to acquire a lock on the session file."""
    path = get_session_json_path(session_id)
    with acquire_file_lock(path, timeout=timeout):
        yield path

def render_markdown(session: Dict[str, Any], state_spec: Optional[Dict[str, Any]] = None) -> str:
    """Render session as markdown summary."""
    meta = session.get("meta", {})
    sid = meta.get("sessionId", "unknown")
    owner = meta.get("owner", "unknown")
    status = meta.get("status", "unknown")
    last_active = meta.get("lastActive", "never")
    
    lines = [
        f"# Session {sid}",
        f"",
        f"- **Owner:** {owner}",
        f"- **Status:** {status}",
        f"- **Last Active:** {last_active}",
        f"",
        f"## Tasks",
    ]
    
    tasks = session.get("tasks", {})
    if not tasks:
        lines.append("_No tasks registered._")
    else:
        for tid, t in tasks.items():
            t_status = t.get("status", "unknown")
            lines.append(f"- **{tid}**: {t_status}")
            
    lines.append("")
    lines.append("## QA")
    qa = session.get("qa", {})
    if not qa:
        lines.append("_No QA registered._")
    else:
        for qid, q in qa.items():
            q_status = q.get("status", "unknown")
            lines.append(f"- **{qid}**: {q_status}")
            
    return "\\n".join(lines)


# ============================================================================
# High-level session operations (formerly in lib.py)
# ============================================================================

def _get_worktree_base() -> Path:
    """Get the worktree base directory from configuration."""
    from ..config import ConfigManager
    cfg = ConfigManager().load_config(validate=False)
    wt = (cfg.get("worktrees") or {}).get("baseDirectory")
    if wt:
        base = Path(wt)
        return base if base.is_absolute() else (PathResolver.resolve_project_root().parent / base).resolve()
    root = PathResolver.resolve_project_root()
    return (root.parent / f"{root.name}-worktrees").resolve()


def _append_state_history(data: Dict[str, Any], from_state: str, to_state: str, reason: Optional[str]) -> None:
    """Append a state transition to the session's history."""
    history = list(data.get("state_history") or data.get("stateHistory") or [])
    history.append({
        "from": from_state,
        "to": to_state,
        "timestamp": io_utc_timestamp(),
        "reason": reason,
    })
    data["state_history"] = history


def ensure_session(session_id: str, state: str = "Active") -> Path:
    """Create a session directory and session.json in the requested state.

    Returns the session directory path.
    """
    from .validation import validate_session_id_format

    sid = sanitize_session_id(session_id)
    target_state = state.lower()
    validate_session_id_format(sid)

    sess_dir = _session_dir(target_state, sid)
    sess_dir.mkdir(parents=True, exist_ok=True)
    sess_json = sess_dir / "session.json"

    if sess_json.exists():
        data = io_read_json_safe(sess_json)
    else:
        data = {
            "id": sid,
            "state": state.title(),
            "worktreeBase": str(_get_worktree_base()),
            "meta": {
                "sessionId": sid,
                "createdAt": io_utc_timestamp(),
                "lastActive": io_utc_timestamp(),
                "status": target_state,
            },
            "metadata": {},
            "tasks": {},
            "qa": {},
            "state_history": [],
            "activityLog": [
                {"timestamp": io_utc_timestamp(), "message": "Session created"}
            ],
        }

    # Default readiness flag required by state-machine conditions
    if "ready" not in data:
        data["ready"] = True

    # Sync state and persist
    data["state"] = state.title()
    io_atomic_write_json(sess_json, data)

    return sess_dir


def transition_state(
    session: Union[str, Path],
    target_state: str,
    *,
    reason: Optional[str] = None
) -> bool:
    """Transition session to a new state with validation.

    Accepts either a session id or a path to the session directory.
    Returns True on success, False on failure for Path-based calls.
    Raises exceptions for ID-based calls on failure.
    """
    from . import state as session_state

    target = target_state.lower()
    if isinstance(session, Path):
        sess_dir = session.resolve()
        sid = sess_dir.name
        json_path = sess_dir / "session.json"
    else:
        sid = session
        try:
            json_path = get_session_json_path(sid)
            sess_dir = json_path.parent
        except Exception:
            sess_dir = _session_dir(target, sid)
            json_path = sess_dir / "session.json"

    try:
        data = io_read_json_safe(json_path)
    except FileNotFoundError:
        if isinstance(session, Path):
            return False
        raise SessionNotFoundError(f"session {sid} not found")
    except Exception:
        if isinstance(session, Path):
            return False
        raise

    if "ready" not in data:
        data["ready"] = True

    current = str(data.get("state") or "").lower() or "active"
    try:
        session_state.validate_transition(current, target, context={"session": data})
    except Exception:
        # Path-based calls return False on invalid transition
        if isinstance(session, Path):
            return False
        raise

    data["state"] = target.title()
    _append_state_history(data, current, target, reason)
    io_atomic_write_json(json_path, data)

    try:
        _move_session_json_to(target, sid)
    except Exception:
        pass

    return True
