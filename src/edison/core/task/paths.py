from __future__ import annotations

"""Path resolution helpers for tasks, QA, and sessions."""

import os
from pathlib import Path
from typing import Dict, List

from edison.core.utils.git import get_repo_root

from ..legacy_guard import enforce_no_legacy_project_root
from ..paths import EdisonPathError, PathResolver
from ..session.config import SessionConfig
from .config import TaskConfig


def _resolve_repo_root() -> Path:
    """Resolve repository root using the canonical PathResolver."""
    try:
        root = PathResolver.resolve_project_root()
    except EdisonPathError as exc:  # pragma: no cover - defensive
        try:
            root = get_repo_root()
        except EdisonPathError as exc2:
            raise RuntimeError(str(exc2)) from exc2
    if root.name == ".edison":
        try:
            root = PathResolver.resolve_project_root()
        except EdisonPathError as exc:  # pragma: no cover - defensive
            raise RuntimeError(str(exc)) from exc
    return root


ROOT = _resolve_repo_root()

if ROOT.name == ".edison":
    raise ValueError(
        f"CRITICAL: Repo root resolved to .edison directory ({ROOT}). "
        f"This indicates a path resolution bug. "
        f"Set AGENTS_PROJECT_ROOT to your actual project root."
    )

enforce_no_legacy_project_root("lib.task.paths")

_SESSION_CONFIG = SessionConfig()
_TASK_CONFIG = TaskConfig(repo_root=ROOT)

TASK_ROOT: Path = _TASK_CONFIG.tasks_root()
QA_ROOT: Path = _TASK_CONFIG.qa_root()

_sessions_rel = _SESSION_CONFIG.get_session_root_path()
SESSIONS_ROOT: Path = (ROOT / _sessions_rel).resolve()

_TASK_STATES = _TASK_CONFIG.task_states() or ["todo", "wip", "blocked", "done", "validated"]
_QA_STATES = _TASK_CONFIG.qa_states() or ["waiting", "todo", "wip", "done", "validated"]

TASK_DIRS: Dict[str, Path] = {state: (TASK_ROOT / state).resolve() for state in _TASK_STATES}
QA_DIRS: Dict[str, Path] = {state: (QA_ROOT / state).resolve() for state in _QA_STATES}


def _build_session_dirs() -> Dict[str, Path]:
    """Compute on-disk session directories from configuration."""
    state_map = _SESSION_CONFIG.get_session_states()
    base = SESSIONS_ROOT
    return {state: (base / dirname).resolve() for state, dirname in state_map.items()}


SESSION_DIRS: Dict[str, Path] = _build_session_dirs()


def _session_state_dir(state: str) -> Path:
    """Return the on-disk directory for a session state with sane fallbacks."""
    return SESSION_DIRS.get(state.lower()) or (SESSIONS_ROOT / state.lower()).resolve()


def session_state_dir(state: str) -> Path:
    """Public accessor for session state directory (used by tests)."""
    return _session_state_dir(state)


def _session_tasks_dir(session_id: str, state: str) -> Path:
    """Get tasks directory for a session, organized by task state within the session dir.

    Args:
        session_id: Session identifier
        state: Task state (todo, wip, done, etc.) - NOT session state

    Returns:
        Path like .project/sessions/<session_state>/<session_id>/tasks/<task_state>/
    """
    # Find the session's actual location (by session state, not task state)
    try:
        from edison.core.session import store as session_store
        session_json_path = session_store.get_session_json_path(session_id)
        session_base = session_json_path.parent
    except Exception:
        # Fallback: assume session is in wip (active) state
        session_base = _session_state_dir("wip") / session_id

    return (session_base / "tasks" / state.lower()).resolve()


def _session_qa_dir(session_id: str, state: str) -> Path:
    """Get QA directory for a session, organized by QA state within the session dir.

    Args:
        session_id: Session identifier
        state: QA state (waiting, todo, wip, done, etc.) - NOT session state

    Returns:
        Path like .project/sessions/<session_state>/<session_id>/qa/<qa_state>/
    """
    # Find the session's actual location (by session state, not QA state)
    try:
        from edison.core.session import store as session_store
        session_json_path = session_store.get_session_json_path(session_id)
        session_base = session_json_path.parent
    except Exception:
        # Fallback: assume session is in wip (active) state
        session_base = _session_state_dir("wip") / session_id

    return (session_base / "qa" / state.lower()).resolve()


# Metadata line prefixes used across task/QA templates (config-driven)
OWNER_PREFIX_TASK = _TASK_CONFIG.default_prefix("ownerPrefix")
OWNER_PREFIX_QA = _TASK_CONFIG.default_prefix("validatorOwnerPrefix")
STATUS_PREFIX = _TASK_CONFIG.default_prefix("statusPrefix")
CLAIMED_PREFIX = _TASK_CONFIG.default_prefix("claimedPrefix")
LAST_ACTIVE_PREFIX = _TASK_CONFIG.default_prefix("lastActivePrefix")
CONTINUATION_PREFIX = _TASK_CONFIG.default_prefix("continuationPrefix")


def get_pack_context() -> List[str]:
    """Return active packs from merged configuration."""
    try:
        from ..config import ConfigManager  # type: ignore

        cfg = ConfigManager().load_config(validate=False)
        packs = (cfg.get("packs") or {}).get("active") or []
        return [str(x) for x in packs if isinstance(x, str)]
    except Exception:
        return []


def _tasks_root() -> Path:
    return TASK_ROOT


def _qa_root() -> Path:
    return QA_ROOT


def safe_relative(path: Path) -> str:
    """Return path relative to project root, falling back to absolute on error."""
    try:
        return str(Path(path).resolve().relative_to(Path(".").resolve()))
    except Exception:
        return str(Path(path).resolve())


__all__ = [
    "ROOT",
    "TASK_ROOT",
    "QA_ROOT",
    "SESSIONS_ROOT",
    "SESSION_DIRS",
    "TASK_DIRS",
    "QA_DIRS",
    "OWNER_PREFIX_TASK",
    "OWNER_PREFIX_QA",
    "STATUS_PREFIX",
    "CLAIMED_PREFIX",
    "LAST_ACTIVE_PREFIX",
    "CONTINUATION_PREFIX",
    "_session_tasks_dir",
    "_session_qa_dir",
    "_tasks_root",
    "_qa_root",
    "session_state_dir",
    "get_pack_context",
    "safe_relative",
]
