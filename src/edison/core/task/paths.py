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


# Cache holders for lazy initialization - reset by conftest.py for test isolation
_ROOT_CACHE: Path | None = None
_SESSION_CONFIG_CACHE: SessionConfig | None = None
_TASK_CONFIG_CACHE: TaskConfig | None = None
_TASK_ROOT_CACHE: Path | None = None
_QA_ROOT_CACHE: Path | None = None
_SESSIONS_ROOT_CACHE: Path | None = None
_TASK_DIRS_CACHE: Dict[str, Path] | None = None
_QA_DIRS_CACHE: Dict[str, Path] | None = None


def _get_root() -> Path:
    """Lazily resolve and cache ROOT."""
    global _ROOT_CACHE
    if _ROOT_CACHE is None:
        _ROOT_CACHE = _resolve_repo_root()
        if _ROOT_CACHE.name == ".edison":
            raise ValueError(
                f"CRITICAL: Repo root resolved to .edison directory ({_ROOT_CACHE}). "
                f"This indicates a path resolution bug. "
                f"Set AGENTS_PROJECT_ROOT to your actual project root."
            )
        enforce_no_legacy_project_root("lib.task.paths")
    return _ROOT_CACHE


def _get_session_config() -> SessionConfig:
    """Lazily resolve and cache SessionConfig."""
    global _SESSION_CONFIG_CACHE
    if _SESSION_CONFIG_CACHE is None:
        _SESSION_CONFIG_CACHE = SessionConfig()
    return _SESSION_CONFIG_CACHE


def _get_task_config() -> TaskConfig:
    """Lazily resolve and cache TaskConfig."""
    global _TASK_CONFIG_CACHE
    if _TASK_CONFIG_CACHE is None:
        _TASK_CONFIG_CACHE = TaskConfig(repo_root=_get_root())
    return _TASK_CONFIG_CACHE


def _get_task_root() -> Path:
    """Lazily resolve and cache TASK_ROOT."""
    global _TASK_ROOT_CACHE
    if _TASK_ROOT_CACHE is None:
        _TASK_ROOT_CACHE = _get_task_config().tasks_root()
    return _TASK_ROOT_CACHE


def _get_qa_root() -> Path:
    """Lazily resolve and cache QA_ROOT."""
    global _QA_ROOT_CACHE
    if _QA_ROOT_CACHE is None:
        _QA_ROOT_CACHE = _get_task_config().qa_root()
    return _QA_ROOT_CACHE


def _get_sessions_root() -> Path:
    """Lazily resolve and cache SESSIONS_ROOT."""
    global _SESSIONS_ROOT_CACHE
    if _SESSIONS_ROOT_CACHE is None:
        sessions_rel = _get_session_config().get_session_root_path()
        _SESSIONS_ROOT_CACHE = (_get_root() / sessions_rel).resolve()
    return _SESSIONS_ROOT_CACHE


def _get_task_states() -> List[str]:
    """Get task states from config or defaults."""
    return _get_task_config().task_states() or ["todo", "wip", "blocked", "done", "validated"]


def _get_qa_states() -> List[str]:
    """Get QA states from config or defaults."""
    return _get_task_config().qa_states() or ["waiting", "todo", "wip", "done", "validated"]


def _get_task_dirs() -> Dict[str, Path]:
    """Lazily resolve and cache TASK_DIRS."""
    global _TASK_DIRS_CACHE
    if _TASK_DIRS_CACHE is None:
        task_root = _get_task_root()
        _TASK_DIRS_CACHE = {state: (task_root / state).resolve() for state in _get_task_states()}
    return _TASK_DIRS_CACHE


def _get_qa_dirs() -> Dict[str, Path]:
    """Lazily resolve and cache QA_DIRS."""
    global _QA_DIRS_CACHE
    if _QA_DIRS_CACHE is None:
        qa_root = _get_qa_root()
        _QA_DIRS_CACHE = {state: (qa_root / state).resolve() for state in _get_qa_states()}
    return _QA_DIRS_CACHE


# For backward compatibility, expose module-level variables
# that are resolved lazily via __getattr__
def __getattr__(name: str):
    """Lazy module attribute access for backward compatibility."""
    if name == "ROOT":
        return _get_root()
    if name == "TASK_ROOT":
        return _get_task_root()
    if name == "QA_ROOT":
        return _get_qa_root()
    if name == "SESSIONS_ROOT":
        return _get_sessions_root()
    if name == "TASK_DIRS":
        return _get_task_dirs()
    if name == "QA_DIRS":
        return _get_qa_dirs()
    if name == "SESSION_DIRS":
        return _get_session_dirs()
    if name == "_SESSION_CONFIG":
        return _get_session_config()
    if name == "_TASK_CONFIG":
        return _get_task_config()
    if name == "_TASK_STATES":
        return _get_task_states()
    if name == "_QA_STATES":
        return _get_qa_states()
    # Prefix constants - lazily resolved from config
    if name in ("OWNER_PREFIX_TASK", "OWNER_PREFIX_QA", "STATUS_PREFIX",
                "CLAIMED_PREFIX", "LAST_ACTIVE_PREFIX", "CONTINUATION_PREFIX"):
        return _get_prefix_cache()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_SESSION_DIRS_CACHE: Dict[str, Path] | None = None


def _get_session_dirs() -> Dict[str, Path]:
    """Lazily resolve and cache SESSION_DIRS."""
    global _SESSION_DIRS_CACHE
    if _SESSION_DIRS_CACHE is None:
        state_map = _get_session_config().get_session_states()
        base = _get_sessions_root()
        _SESSION_DIRS_CACHE = {state: (base / dirname).resolve() for state, dirname in state_map.items()}
    return _SESSION_DIRS_CACHE


def _session_state_dir(state: str) -> Path:
    """Return the on-disk directory for a session state with sane fallbacks."""
    session_dirs = _get_session_dirs()
    return session_dirs.get(state.lower()) or (_get_sessions_root() / state.lower()).resolve()


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
# These are lazily resolved via __getattr__ to support test isolation
_PREFIX_CACHE: Dict[str, str] | None = None


def _get_prefix_cache() -> Dict[str, str]:
    """Lazily resolve and cache prefix values."""
    global _PREFIX_CACHE
    if _PREFIX_CACHE is None:
        task_config = _get_task_config()
        _PREFIX_CACHE = {
            "OWNER_PREFIX_TASK": task_config.default_prefix("ownerPrefix"),
            "OWNER_PREFIX_QA": task_config.default_prefix("validatorOwnerPrefix"),
            "STATUS_PREFIX": task_config.default_prefix("statusPrefix"),
            "CLAIMED_PREFIX": task_config.default_prefix("claimedPrefix"),
            "LAST_ACTIVE_PREFIX": task_config.default_prefix("lastActivePrefix"),
            "CONTINUATION_PREFIX": task_config.default_prefix("continuationPrefix"),
        }
    return _PREFIX_CACHE


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
    return _get_task_root()


def _qa_root() -> Path:
    return _get_qa_root()


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
