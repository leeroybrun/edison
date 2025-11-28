from __future__ import annotations

"""Path resolution helpers for tasks, QA, and sessions."""

import os
from pathlib import Path
from typing import Dict, List

from ..legacy_guard import enforce_no_legacy_project_root
from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.config.domains import SessionConfig, TaskConfig


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
        _ROOT_CACHE = PathResolver.resolve_project_root()
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
    """Get task states from config.

    Returns:
        List of task states from configuration

    Raises:
        ValueError: If config doesn't provide task states (fail-fast)
    """
    states = _get_task_config().task_states()
    if not states:
        raise ValueError("Configuration must define task states (statemachine.task.states)")
    return states


def _get_qa_states() -> List[str]:
    """Get QA states from config.

    Returns:
        List of QA states from configuration

    Raises:
        ValueError: If config doesn't provide QA states (fail-fast)
    """
    states = _get_task_config().qa_states()
    if not states:
        raise ValueError("Configuration must define QA states (statemachine.qa.states)")
    return states


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


# Public accessor functions (replace __getattr__ magic with explicit functions)

def get_root() -> Path:
    """Get the project root directory."""
    return _get_root()


def get_task_root() -> Path:
    """Get the task root directory."""
    return _get_task_root()


def get_qa_root() -> Path:
    """Get the QA root directory."""
    return _get_qa_root()


def get_sessions_root() -> Path:
    """Get the sessions root directory."""
    return _get_sessions_root()


def get_task_dirs() -> Dict[str, Path]:
    """Get mapping of task states to their directory paths."""
    return _get_task_dirs()


def get_qa_dirs() -> Dict[str, Path]:
    """Get mapping of QA states to their directory paths."""
    return _get_qa_dirs()


def get_session_dirs() -> Dict[str, Path]:
    """Get mapping of session states to their directory paths."""
    return _get_session_dirs()


def get_session_config() -> SessionConfig:
    """Get the cached SessionConfig instance."""
    return _get_session_config()


def get_task_config() -> TaskConfig:
    """Get the cached TaskConfig instance."""
    return _get_task_config()


def get_task_states() -> List[str]:
    """Get task states from configuration."""
    return _get_task_states()


def get_qa_states() -> List[str]:
    """Get QA states from configuration."""
    return _get_qa_states()


def get_owner_prefix_task() -> str:
    """Get the owner prefix for tasks."""
    return _get_prefix_cache()["OWNER_PREFIX_TASK"]


def get_owner_prefix_qa() -> str:
    """Get the owner prefix for QA records."""
    return _get_prefix_cache()["OWNER_PREFIX_QA"]


def get_status_prefix() -> str:
    """Get the status prefix."""
    return _get_prefix_cache()["STATUS_PREFIX"]


def get_claimed_prefix() -> str:
    """Get the claimed timestamp prefix."""
    return _get_prefix_cache()["CLAIMED_PREFIX"]


def get_last_active_prefix() -> str:
    """Get the last active timestamp prefix."""
    return _get_prefix_cache()["LAST_ACTIVE_PREFIX"]


def get_continuation_prefix() -> str:
    """Get the continuation ID prefix."""
    return _get_prefix_cache()["CONTINUATION_PREFIX"]


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
        from edison.core.session.repository import SessionRepository
        repo = SessionRepository()
        session_json_path = repo.get_session_json_path(session_id)
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
        from edison.core.session.repository import SessionRepository
        repo = SessionRepository()
        session_json_path = repo.get_session_json_path(session_id)
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


def safe_relative(path: Path) -> str:
    """Return path relative to project root, falling back to absolute on error."""
    try:
        return str(Path(path).resolve().relative_to(Path(".").resolve()))
    except Exception:
        return str(Path(path).resolve())


__all__ = [
    # Public getter functions (explicit, type-safe)
    "get_root",
    "get_task_root",
    "get_qa_root",
    "get_sessions_root",
    "get_task_dirs",
    "get_qa_dirs",
    "get_session_dirs",
    "get_session_config",
    "get_task_config",
    "get_task_states",
    "get_qa_states",
    "get_owner_prefix_task",
    "get_owner_prefix_qa",
    "get_status_prefix",
    "get_claimed_prefix",
    "get_last_active_prefix",
    "get_continuation_prefix",
    # Path resolution helpers
    "_session_tasks_dir",
    "_session_qa_dir",
    "session_state_dir",
    # Utility functions
    "safe_relative",
]
