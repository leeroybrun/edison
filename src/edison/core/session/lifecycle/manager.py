"""Session manager facade.

This module provides the SessionManager class that consolidates session
lifecycle operations including creation, state transitions, and queries.

The module-level functions provide a functional API for CLI and scripts.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..core.id import validate_session_id, SessionIdError
from ..core.naming import generate_session_id
from ..current import get_current_session, set_current_session, clear_current_session
from ..core.models import Session
from ..persistence.repository import SessionRepository
from .._config import get_config
from edison.core.utils.paths import PathResolver
from edison.core.config.domains.session import SessionConfig
from edison.core.state.validator import StateValidator
from edison.core.state import StateTransitionError
from ...exceptions import SessionError, ValidationError

logger = logging.getLogger(__name__)


def _validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format, converting SessionIdError to ValidationError.
    
    Args:
        session_id: The session ID to validate
        
    Returns:
        True if validation passes
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        validate_session_id(session_id)
        return True
    except SessionIdError as e:
        raise ValidationError(str(e)) from e


def _get_worktree_config():
    from ._config import get_config

    return get_config().get_worktree_config()

def create_session(
    session_id: str,
    owner: str,
    mode: str = "start",
    install_deps: Optional[bool] = None,
    *,
    create_wt: bool = True
) -> Path:
    """Create a new session with optional worktree."""
    _validate_session_id_format(session_id)
    project_root = PathResolver.resolve_project_root()
    repo = SessionRepository(project_root=project_root)
    config = SessionConfig(repo_root=project_root)

    if repo.exists(session_id):
        raise SessionError(f"Session {session_id} already exists", session_id=session_id)

    # Create session entity
    sid = validate_session_id(session_id)
    initial_state = config.get_initial_session_state()
    entity = Session.create(sid, owner=owner, state=initial_state)
    repo.create(entity)

    sess = repo.get(session_id)
    if not sess:
        raise SessionError("Failed to create session", session_id=session_id)

    # Handle worktree creation if configured or requested
    # Delegate to worktree module for all git operations

    data = sess.to_dict()
    data.setdefault("git", {})
    wt_cfg = _get_worktree_config()
    base_branch = wt_cfg.get("baseBranch")
    if base_branch:
        data["git"].setdefault("baseBranch", base_branch)

    in_git_repo = (project_root / ".git").exists()

    if create_wt and in_git_repo:
        try:
            from .. import worktree

            wt_path, branch = worktree.create_worktree(session_id, install_deps=install_deps)
            if wt_path and branch:
                # Use centralized helper to construct git metadata
                git_meta = worktree.prepare_session_git_metadata(session_id, wt_path, branch)
                data["git"].update(git_meta)
        except Exception as exc:
            raise SessionError(f"Failed to create worktree for session {session_id}: {exc}", session_id=session_id) from exc

    repo.save(Session.from_dict(data))
    return repo.get_session_json_path(session_id)

def get_session(session_id: str) -> Dict[str, Any]:
    """Get a session by ID."""
    project_root = PathResolver.resolve_project_root()
    repo = SessionRepository(project_root=project_root)
    session = repo.get(session_id)
    if not session:
        raise SessionError(f"Session {session_id} not found", session_id=session_id)
    return session.to_dict()

def list_sessions(state: Optional[str] = None) -> List[str]:
    """List sessions, optionally filtered by state."""
    project_root = PathResolver.resolve_project_root()
    repo = SessionRepository(project_root=project_root)
    if state:
        return [s.id for s in repo.list_by_state(state)]
    return [s.id for s in repo.get_all()]

def transition_session(session_id: str, target_state: str) -> None:
    """Transition a session to a new state."""
    project_root = PathResolver.resolve_project_root()
    repo = SessionRepository(project_root=project_root)
    validator = StateValidator(repo_root=project_root)

    sid = validate_session_id(session_id)
    entity = repo.get(sid)
    if entity is None:
        raise FileNotFoundError(f"Session {sid} not found")

    current = str(entity.state).lower()
    target = str(target_state).lower()

    # Validate via unified state validator
    validator.ensure_transition("session", current, target)

    entity.record_transition(current, target)
    entity.state = target
    repo.save(entity)

def touch_session(session_id: str) -> None:
    """Update session lastActive timestamp."""
    try:
        project_root = PathResolver.resolve_project_root()
        repo = SessionRepository(project_root=project_root)
        sess = repo.get(session_id)
        if sess:
            sess.add_activity("touched")
            repo.save(sess)
    except Exception:
        pass

def render_markdown(session: Dict[str, Any], state_spec: Optional[Dict[str, Any]] = None) -> str:
    """Render session as markdown summary."""
    meta = session.get("meta", {})
    sid = meta.get("sessionId", session.get("id", "unknown"))
    owner = meta.get("owner", "unknown")
    status = meta.get("status", session.get("state", "unknown"))
    last_active = meta.get("lastActive", "never")

    lines = [
        f"# Session {sid}",
        "",
        f"- **Owner:** {owner}",
        f"- **Status:** {status}",
        f"- **Last Active:** {last_active}",
        "",
        "## Tasks",
    ]

    tasks = session.get("tasks", {})
    if not tasks:
        lines.append("_No tasks registered._")
    else:
        for tid, t in tasks.items():
            t_status = t.get("status", "unknown") if isinstance(t, dict) else "unknown"
            lines.append(f"- **{tid}**: {t_status}")

    lines.append("")
    lines.append("## QA")
    qa = session.get("qa", {})
    if not qa:
        lines.append("_No QA registered._")
    else:
        for qid, q in qa.items():
            q_status = q.get("status", "unknown") if isinstance(q, dict) else "unknown"
            lines.append(f"- **{qid}**: {q_status}")

    return "\n".join(lines)


class SessionManager:
    """Consolidated session manager for lifecycle operations.

    Provides high-level session operations including:
    - Creating sessions with validation
    - State transitions with state machine validation
    - Session queries

    Uses SessionRepository for persistence and StateValidator for transitions.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = get_config(self.project_root)
        self._session_config = SessionConfig(repo_root=self.project_root)
        self._repo = SessionRepository(project_root=self.project_root)
        self._validator = StateValidator(repo_root=self.project_root)

    @property
    def repo(self) -> SessionRepository:
        """Get the underlying repository (for direct access when needed)."""
        return self._repo

    def create(
        self,
        session_id: str,
        *,
        owner: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Create a new session.

        Args:
            session_id: Session identifier
            owner: Session owner
            metadata: Additional metadata

        Returns:
            Path to session.json file
        """
        sid = validate_session_id(session_id)
        initial_state = self._session_config.get_initial_session_state()

        entity = Session.create(sid, owner=owner, state=initial_state)
        self._repo.create(entity)
        return self._repo.get_session_json_path(sid)

    def transition(self, session_id: str, to_state: str) -> Path:
        """Transition a session to a new state.

        Args:
            session_id: Session identifier
            to_state: Target state

        Returns:
            Path to session.json file

        Raises:
            FileNotFoundError: If session not found
            StateTransitionError: If transition is invalid
        """
        sid = validate_session_id(session_id)
        entity = self._repo.get(sid)
        if entity is None:
            raise FileNotFoundError(f"Session {sid} not found")

        current = str(entity.state).lower()
        target = str(to_state).lower()

        # Validate via unified state validator
        self._validator.ensure_transition("session", current, target)

        entity.record_transition(current, target)
        entity.state = target
        self._repo.save(entity)

        return self._repo.get_session_json_path(sid)

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        owner: Optional[str] = None,
    ) -> Path:
        """Create a new session with auto-generated ID if not provided.

        This method provides a higher-level API that handles ID generation.

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            metadata: Additional metadata
            owner: Session owner

        Returns:
            Path to session.json file
        """
        sid = session_id or self._generate_session_id()

        path = self.create(session_id=sid, owner=owner, metadata=metadata)

        # Update metadata for downstream consumers
        session = self._repo.get(sid)
        if session:
            meta = session.to_dict().get("meta", {})
            strategy_used = self._config.get_naming_config().get("strategy")
            if strategy_used:
                meta["namingStrategy"] = strategy_used
            if owner:
                meta["orchestratorProfile"] = owner
            session_dict = session.to_dict()
            session_dict["meta"] = meta
            self._repo.save(Session.from_dict(session_dict))
        return path

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Load a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data as dictionary

        Raises:
            SessionError: If session not found
        """
        session = self._repo.get(session_id)
        if not session:
            raise SessionError(f"Session {session_id} not found", session_id=session_id)
        return session.to_dict()

    def transition_state(self, session_id: str, to_state: str) -> Path:
        """Transition a session to a new state (alias for transition).

        Args:
            session_id: Session identifier
            to_state: Target state

        Returns:
            Path to session.json file
        """
        return self.transition(session_id, to_state)

    # --- Internal helpers -------------------------------------------------
    def _generate_session_id(self) -> str:
        """Generate a new session ID."""
        return generate_session_id()
