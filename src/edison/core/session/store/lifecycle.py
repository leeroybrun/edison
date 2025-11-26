"""Session lifecycle operations."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union, Iterator
from contextlib import contextmanager

from ...legacy_guard import enforce_no_legacy_project_root
from ...file_io.utils import (
    write_json_safe as io_atomic_write_json,
    read_json_safe as io_read_json_safe,
    ensure_directory,
)
from ...utils.time import utc_timestamp as io_utc_timestamp
from ...exceptions import SessionNotFoundError
from ...paths.resolver import PathResolver

from . import _shared
from ._shared import (
    sanitize_session_id,
    _session_dir,
)

logger = logging.getLogger(__name__)

# Fail-fast if running against a legacy (pre-Edison) project root
enforce_no_legacy_project_root("lib.session.store.lifecycle")


def _get_worktree_base() -> Path:
    """Get the worktree base directory from configuration."""
    from ..config import ConfigManager
    from ..utils.project_config import substitute_project_tokens

    cfg = ConfigManager().load_config(validate=False)
    wt = (cfg.get("worktrees") or {}).get("baseDirectory") or "../{PROJECT_NAME}-worktrees"
    root = PathResolver.resolve_project_root()
    expanded = substitute_project_tokens(str(wt), root)
    base = Path(expanded)
    if base.is_absolute():
        return base
    anchor = root if (base.parts and base.parts[0] == "..") else root.parent
    return (anchor / base).resolve()


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


def _move_session_json_to(status: str, session_id: str) -> Path:
    """Move session directory to a new lifecycle state."""
    from .discovery import get_session_json_path

    sid = sanitize_session_id(session_id)
    try:
        src = get_session_json_path(sid)
    except SessionNotFoundError:
        raise FileNotFoundError(f"Session {sid} not found")

    dest_dir = _session_dir(status, sid)
    dest = dest_dir / "session.json"
    ensure_directory(dest_dir)

    try:
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.move(str(src.parent), str(dest_dir))
        return dest / "session.json"
    except Exception as e:
        logger.error("Failed to move session JSON for %s to %s: %s", session_id, status, e)
        raise


@contextmanager
def acquire_session_lock(session_id: str, *, timeout: float = 5.0) -> Iterator[Path]:
    """Context manager to acquire a lock on the session file."""
    from ...file_io.locking import acquire_file_lock
    from .discovery import get_session_json_path

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


def ensure_session(session_id: str, state: str = "Active") -> Path:
    """Create a session directory and session.json in the requested state.

    Returns the session directory path.
    """
    from ..validation import validate_session_id_format

    sid = sanitize_session_id(session_id)
    target_state = state.lower()
    validate_session_id_format(sid)

    sess_dir = _session_dir(target_state, sid)
    ensure_directory(sess_dir)
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
    from .. import state as session_state
    from .discovery import get_session_json_path

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
