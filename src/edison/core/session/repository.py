"""Session repository for file-based persistence.

This module provides the SessionRepository class that implements
the repository pattern for session entities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    BaseRepository,
    FileRepositoryMixin,
    EntityId,
    PersistenceError,
    EntityNotFoundError,
)
from edison.core.legacy_guard import enforce_no_legacy_project_root
from edison.core.utils.paths import PathResolver
from edison.core.utils.io import read_json, write_json_atomic, ensure_directory

from .models import Session
from ._config import get_config

enforce_no_legacy_project_root("session.repository")


class SessionRepository(BaseRepository[Session], FileRepositoryMixin[Session]):
    """File-based repository for session entities.

    Sessions are stored as JSON files in state-based directories using NESTED layout:
    - .project/sessions/wip/{session_id}/session.json
    - .project/sessions/done/{session_id}/session.json
    - .project/sessions/validated/{session_id}/session.json

    Each session has its own directory containing session.json and related files (tasks, qa, etc).
    """
    
    entity_type: str = "session"
    file_extension: str = ".json"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize repository.
        
        Args:
            project_root: Project root directory
        """
        super().__init__(project_root)
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = get_config(self.project_root)
    
    # ---------- Path Resolution ----------
    
    def _get_sessions_root(self) -> Path:
        """Get the sessions root directory."""
        root_rel = self._config.get_session_root_path()
        return (self.project_root / root_rel).resolve()
    
    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a session state.
        
        Maps state names to directory names using config.
        """
        state_map = self._config.get_session_states()
        dirname = state_map.get(state, state)
        return self._get_sessions_root() / dirname
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search in order."""
        return self._config.get_session_lookup_order()
    
    def _resolve_entity_path(
        self,
        entity_id: EntityId,
        state: Optional[str] = None,
    ) -> Path:
        """Resolve path for a session file.

        Sessions are stored as: {state_dir}/{session_id}/session.json

        Args:
            entity_id: Session identifier
            state: Session state

        Returns:
            Path to session JSON file
        """
        if state:
            state_dir = self._get_state_dir(state)
        else:
            # Default to initial state
            initial = self._config.get_initial_session_state()
            state_dir = self._get_state_dir(initial)

        return state_dir / entity_id / "session.json"
    
    def _get_entity_filename(self, entity_id: EntityId) -> str:
        """Get the filename for a session entity."""
        return "session.json"
    
    def _find_entity_path(self, entity_id: EntityId) -> Optional[Path]:
        """Find a session file by searching state directories."""
        for state in self._get_states_to_search():
            path = self._resolve_entity_path(entity_id, state)
            if path.exists():
                return path
        return None
    
    # ---------- CRUD Implementation ----------
    
    def _do_create(self, entity: Session) -> Session:
        """Create a new session."""
        path = self._resolve_entity_path(entity.id, entity.state)

        # Ensure state directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write session JSON
        data = entity.to_dict()
        write_json_atomic(path, data, acquire_lock=False)

        return entity
    
    def _do_get(self, entity_id: EntityId) -> Optional[Session]:
        """Get a session by ID."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return None
        
        try:
            data = read_json(path)
            return Session.from_dict(data)
        except Exception:
            return None
    
    def _do_save(self, entity: Session) -> None:
        """Save a session."""
        current_path = self._find_entity_path(entity.id)
        target_path = self._resolve_entity_path(entity.id, entity.state)

        if current_path is None:
            # New session - create it
            self._do_create(entity)
            return

        # Check if state changed (need to move directory)
        if current_path != target_path:
            # With nested layout, we need to move the entire session directory
            # current_path: .project/sessions/wip/session-id/session.json
            # target_path: .project/sessions/done/session-id/session.json
            current_session_dir = current_path.parent
            target_session_dir = target_path.parent

            # Ensure target state directory exists
            target_session_dir.parent.mkdir(parents=True, exist_ok=True)

            # Move entire session directory (preserves tasks, qa, etc.)
            current_session_dir.rename(target_session_dir)

            # Update path for writing
            current_path = target_path

        # Write updated content
        data = entity.to_dict()
        write_json_atomic(current_path, data, acquire_lock=False)
    
    def _do_delete(self, entity_id: EntityId) -> bool:
        """Delete a session."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return False

        # Delete session file
        path.unlink()
        return True
    
    def _do_exists(self, entity_id: EntityId) -> bool:
        """Check if a session exists."""
        return self._find_entity_path(entity_id) is not None
    
    # ---------- Query Implementation ----------
    
    def _do_find(self, **criteria: Any) -> List[Session]:
        """Find sessions matching criteria."""
        results: List[Session] = []
        
        for session in self._do_list_all():
            match = True
            for key, value in criteria.items():
                session_value = getattr(session, key, None)
                if session_value != value:
                    match = False
                    break
            if match:
                results.append(session)
        
        return results
    
    def _do_list_by_state(self, state: str) -> List[Session]:
        """List sessions in a given state."""
        state_dir = self._get_state_dir(state)
        if not state_dir.exists():
            return []

        sessions: List[Session] = []
        # With nested layout, each session has its own directory with session.json
        for session_dir in state_dir.iterdir():
            if not session_dir.is_dir():
                continue

            json_path = session_dir / "session.json"
            if not json_path.exists():
                continue

            try:
                data = read_json(json_path)
                session = Session.from_dict(data)
                sessions.append(session)
            except Exception:
                continue

        return sessions
    
    def _do_list_all(self) -> List[Session]:
        """List all sessions."""
        sessions: List[Session] = []
        seen_ids: set = set()
        
        for state in self._get_states_to_search():
            for session in self._do_list_by_state(state):
                if session.id not in seen_ids:
                    sessions.append(session)
                    seen_ids.add(session.id)
        
        return sessions
    
    # ---------- Session-specific Methods ----------
    
    def find_by_owner(self, owner: str) -> List[Session]:
        """Find sessions belonging to an owner."""
        return self._do_find(owner=owner)
    
    def ensure_session(self, session_id: str, state: str = "active") -> Path:
        """Ensure a session file exists.

        Creates the session if it doesn't exist.

        Args:
            session_id: Session identifier
            state: Initial state for new sessions

        Returns:
            Path to session state directory
        """
        path = self._find_entity_path(session_id)
        if path:
            return path.parent

        # Create new session
        session = Session.create(session_id, state=state.lower())
        self.create(session)
        return self._resolve_entity_path(session_id, session.state).parent
    
    def get_session_json_path(self, session_id: str) -> Path:
        """Get the path to a session's JSON file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Path to session.json
            
        Raises:
            EntityNotFoundError: If session not found
        """
        path = self._find_entity_path(session_id)
        if path is None:
            raise EntityNotFoundError(
                f"Session {session_id} not found",
                entity_type="session",
                entity_id=session_id,
            )
        return path


__all__ = [
    "SessionRepository",
]


