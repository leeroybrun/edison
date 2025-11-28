"""Session-scoped repository mixin.

This module provides a mixin class that adds session-scoped record
discovery to repositories. It handles:

- Session base path discovery
- Session record path resolution
- Combined global + session directory search

Used by TaskRepository and QARepository for session-scoped records.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generic, List, Optional, TypeVar

from .base import EntityId
from .protocols import Entity

T = TypeVar("T", bound=Entity)


class SessionScopedMixin(Generic[T]):
    """Mixin providing session-scoped record discovery.

    This mixin adds methods for finding entities that may be stored in
    session-specific directories in addition to global state directories.

    The mixin expects the repository to define:
    - project_root: Optional[Path] - Project root directory
    - _get_entity_filename(entity_id) -> str - Get filename for entity
    - _get_state_dir(state) -> Path - Get global state directory
    - _get_states_to_search() -> List[str] - Get states to search

    Subclasses must set:
    - record_type: str - "task" or "qa"
    - record_subdir: str - "tasks" or "qa" (directory name in session)
    """

    # Override in subclass
    record_type: str = "record"  # "task" or "qa"
    record_subdir: str = "records"  # "tasks" or "qa"

    def _get_session_bases(self, session_id: Optional[str] = None) -> List[Path]:
        """Get session base paths to search.

        Delegates to session.paths.get_session_bases for session path resolution.

        Args:
            session_id: Optional session ID to target specific session

        Returns:
            List of session base paths
        """
        from edison.core.session.paths import get_session_bases

        project_root = getattr(self, "project_root", None)
        return get_session_bases(session_id=session_id, project_root=project_root)

    def _resolve_session_record_path(
        self,
        record_id: str,
        session_id: str,
        state: str,
    ) -> Path:
        """Resolve path for a record in a session directory.

        Delegates to session.paths.resolve_session_record_path for path resolution.

        Args:
            record_id: Record identifier
            session_id: Session identifier
            state: Record state

        Returns:
            Path where the record should be stored
        """
        from edison.core.session.paths import resolve_session_record_path

        project_root = getattr(self, "project_root", None)
        return resolve_session_record_path(
            record_id=record_id,
            session_id=session_id,
            state=state,
            record_type=self.record_type,
            project_root=project_root,
        )

    def _find_entity_path_with_sessions(self, entity_id: EntityId) -> Optional[Path]:
        """Find entity path, checking both global and session directories.

        This method searches for an entity file in:
        1. Global state directories (e.g., .project/tasks/todo/)
        2. Session directories (e.g., .project/sessions/wip/sess-123/tasks/todo/)

        Args:
            entity_id: Entity identifier

        Returns:
            Path to entity file if found, None otherwise
        """
        # Get filename from the repository
        filename = self._get_entity_filename(entity_id)  # type: ignore

        # 1. Check global directories
        for state in self._get_states_to_search():  # type: ignore
            path = self._get_state_dir(state) / filename  # type: ignore
            if path.exists():
                return path

        # 2. Check session directories
        for base in self._get_session_bases():
            for state in self._get_states_to_search():  # type: ignore
                # Session structure: {base}/{record_subdir}/{state}/{filename}
                path = base / self.record_subdir / state / filename
                if path.exists():
                    return path

        return None


__all__ = [
    "SessionScopedMixin",
]
