"""Test helper functions for session operations.

This module provides convenience functions for tests using the new
SessionRepository and SessionService APIs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union, Dict, Any, Iterator

from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.lifecycle.manager import SessionManager
from edison.core.session.worktree.config_helpers import (
    _get_worktree_base,
    _get_project_name as _core_get_project_name,
)
from edison.core.session.lifecycle.transaction import (
    ValidationTransaction,
    validation_transaction as _core_validation_transaction,
)
from edison.core.session.lifecycle.recovery import (
    recover_incomplete_validation_transactions as _core_recover_incomplete_validation_transactions,
)
from edison.core.session.persistence.database import (
    _get_database_url as _core_get_database_url,
)


def ensure_session(session_id: str, state: str = "active") -> Path:
    """Ensure a session exists, creating it if necessary."""
    repo = SessionRepository()
    session_dir = repo.ensure_session(session_id, state=state)
    # Make tests robust to re-runs where a prior session might be considered expired.
    # `ensure_session` in tests means "usable now", so refresh lastActive.
    sess = repo.get(session_id)
    if sess is not None:
        sess.metadata.touch()
        repo.save(sess)
    return session_dir


def load_session(session_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Load a session by ID."""
    repo = SessionRepository()
    session = repo.get(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    return session.to_dict()


def transition_state(
    session_id: Union[str, Path], to_state: str, reason: Optional[str] = None
) -> bool:
    """Transition a session to a new state.

    Args:
        session_id: Session ID as string or Path (extracts directory name if Path)
        to_state: Target state to transition to
        reason: Optional reason for the transition

    Returns:
        bool: True if transition succeeded, False if it failed
    """
    # Handle Path input - extract session ID from directory name
    if isinstance(session_id, Path):
        session_id = session_id.name

    mgr = SessionManager()
    try:
        mgr.transition_state(str(session_id), to_state, reason=reason)
        return True
    except Exception:
        return False


def close_session(session_id: str) -> Path:
    """Close a session (transition to closing state)."""
    mgr = SessionManager()
    mgr.transition_state(session_id, "closing")
    repo = SessionRepository()
    return repo.get_session_json_path(session_id).parent


def validate_session(session_id: str) -> Path:
    """Validate a session (transition to validated state)."""
    mgr = SessionManager()
    mgr.transition_state(session_id, "validated")
    repo = SessionRepository()
    return repo.get_session_json_path(session_id).parent


def get_session_state(session_dir: Path) -> str:
    """Get the current state of a session from its directory."""
    json_path = Path(session_dir) / "session.json"
    if not json_path.exists():
        raise ValueError("session.json missing")
    text = json_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid session.json") from exc
    if "state" not in data:
        raise ValueError("session state missing")
    return str(data["state"])


def handle_timeout(session_dir: Path) -> Path:
    """Move a session to recovery state on timeout."""
    from edison.core.session.lifecycle.recovery import handle_timeout as _handle_timeout

    return _handle_timeout(Path(session_dir).resolve())


def validation_transaction(session_id: str, wave: str) -> Iterator[ValidationTransaction]:
    """Context manager for validation transactions.

    This is a test helper wrapper around the core validation_transaction
    context manager from edison.core.session.lifecycle.transaction.

    Args:
        session_id: The session ID for the validation transaction
        wave: The validation wave identifier

    Yields:
        ValidationTransaction: The transaction object that can be committed or aborted

    Example:
        >>> with validation_transaction(session_id="sess-001", wave="wave1") as tx:
        ...     # Write validation artifacts to tx.staging_root
        ...     tx.commit()
    """
    return _core_validation_transaction(session_id=session_id, wave=wave)


def _get_project_name() -> str:
    """Get the active project name from configuration.

    This is a test helper wrapper around the core _get_project_name
    function from edison.core.session.worktree.config_helpers.

    Returns:
        str: The project name resolved from config, env, or repo folder name

    Raises:
        ValueError: If project name cannot be determined
    """
    return _core_get_project_name()


def _get_database_url() -> str:
    """Get the database URL from configuration.

    This is a test helper wrapper around the core _get_database_url
    function from edison.core.session.persistence.database.

    Returns:
        str: The database URL from configuration or environment

    Raises:
        ValueError: If database.url is not configured when database.enabled is true
    """
    return _core_get_database_url()


def recover_incomplete_validation_transactions(session_id: str) -> int:
    """Recover incomplete validation transactions for a session.

    This is a test helper wrapper around the core function from
    edison.core.session.lifecycle.recovery.

    Args:
        session_id: The session ID to recover transactions for

    Returns:
        int: Number of recovered transactions
    """
    return _core_recover_incomplete_validation_transactions(session_id)


def get_session_json_path(base_path: Path, state: str, session_id: str) -> Path:
    """Get the path to a session's JSON file using the NESTED layout.

    Sessions are stored as: {base_path}/sessions/{state}/{session_id}/session.json

    Args:
        base_path: Base path (project root or .project directory)
        state: Session state (wip, active, validated, etc.)
        session_id: Session identifier

    Returns:
        Path: Path to the session.json file
    """
    return base_path / "sessions" / state / session_id / "session.json"


def get_session_dir_path(base_path: Path, state: str, session_id: str) -> Path:
    """Get the path to a session's directory using the NESTED layout.

    Sessions are stored in: {base_path}/sessions/{state}/{session_id}/

    Args:
        base_path: Base path (project root or .project directory)
        state: Session state (wip, active, validated, etc.)
        session_id: Session identifier

    Returns:
        Path: Path to the session directory
    """
    return base_path / "sessions" / state / session_id
