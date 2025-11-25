"""Session layout detection utilities.

These helpers normalize how session-aware code locates the on-disk base
directory for tasks/qa. Repositories may store ``session.json`` either as a
legacy *flat* file (``.project/sessions/<state>/<sid>.json``) or inside a
session directory (``.../<sid>/session.json``). Some fixtures also persist a
``parent`` hint inside the session payload. The helpers below determine the
effective base directory for record storage regardless of layout.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional


def _session_id(session: Dict[str, Any]) -> str:
    """Extract a session id from common payload shapes."""
    return (
        str(session.get("id") or "")
        or str(session.get("sessionId") or "")
        or str((session.get("meta") or {}).get("sessionId") or "")
    )


def _parent_path(session: Dict[str, Any], session_path: Optional[Path]) -> Path:
    """Determine the parent directory anchor for a session.

    Priority:
      1) explicit ``parent`` (or ``parentPath``) entry in the session dict
      2) directory containing the provided ``session_path``
      3) empty Path (caller handles fallback)
    """

    raw_parent = session.get("parent") or session.get("parentPath")
    if raw_parent:
        try:
            return Path(raw_parent)
        except Exception:
            pass

    if session_path:
        try:
            return Path(session_path).parent
        except Exception:
            pass

    return Path("")


def detect_layout(
    session: Dict[str, Any],
    *,
    session_path: Optional[Path] = None,
) -> Literal["flat", "nested"]:
    """Detect whether a session uses *flat* or *nested* layout.

    Flat layout
      - The parent directory already includes the session id
        (e.g., ``.../sessions/wip/<sid>``)

    Nested layout
      - The parent directory is the lifecycle directory, and the session id
        must be appended (e.g., ``.../sessions/wip`` + ``<sid>``)
    """

    session_id = _session_id(session)
    parent = _parent_path(session, session_path)
    parent_str = str(parent)

    if not session_id or parent_str in {"", "."}:
        return "flat"

    # If the parent directory already ends with the session id, treat as flat
    if parent.name == session_id or parent_str.endswith(f"/{session_id}"):
        return "flat"

    return "nested"


def get_session_base_path(
    session: Dict[str, Any],
    *,
    session_path: Optional[Path] = None,
) -> Path:
    """Return the base directory that holds tasks/qa for a session.

    For flat layouts, this is the parent directory itself (already scoped by
    session id). For nested layouts, append the session id to the parent.
    Falls back to ``Path()`` when metadata is incomplete to keep callers
    resilient in partially-initialized fixtures.
    """

    session_id = _session_id(session)
    parent = _parent_path(session, session_path)

    layout = detect_layout(session, session_path=session_path)

    if layout == "nested" and session_id:
        return (parent / session_id).resolve()

    # Flat or unknown layout
    if str(parent) not in {"", "."}:
        return Path(parent).resolve()

    # As a last resort, fall back to a session-scoped directory name so
    # callers still produce deterministic paths.
    return Path(session_id or ".").resolve()

