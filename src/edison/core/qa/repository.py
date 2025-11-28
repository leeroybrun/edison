"""QA repository for file-based persistence.

This module provides the QARepository class that implements
the repository pattern for QA record entities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    BaseRepository,
    FileRepositoryMixin,
    SessionScopedMixin,
    EntityId,
    EntityMetadata,
    PersistenceError,
)
from edison.core.utils.paths import PathResolver
from edison.core.utils.text import parse_html_comment, format_html_comment, parse_title
from edison.core.config.domains import TaskConfig

from .models import QARecord


class QARepository(
    BaseRepository[QARecord],
    FileRepositoryMixin[QARecord],
    SessionScopedMixin[QARecord],
):
    """File-based repository for QA record entities.

    QA records are stored as Markdown files in state-based directories:
    - .project/qa/waiting/
    - .project/qa/todo/
    - .project/qa/wip/
    - .project/qa/done/
    - .project/qa/validated/

    Supports session-scoped storage via SessionScopedMixin.
    """

    entity_type: str = "qa"
    file_extension: str = ".md"

    # SessionScopedMixin configuration
    record_type: str = "qa"
    record_subdir: str = "qa"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize repository.

        Args:
            project_root: Project root directory
        """
        super().__init__(project_root)
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
    
    # ---------- Path Resolution ----------
    
    def _get_qa_root(self) -> Path:
        """Get the QA root directory."""
        return self._config.qa_root()
    
    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a QA state."""
        return self._get_qa_root() / state
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search from configuration.

        Returns:
            List of QA state names

        Raises:
            ValueError: If config doesn't provide QA states
        """
        states = self._config.qa_states()
        if not states:
            raise ValueError("Configuration must define QA states (statemachine.qa.states)")
        return states
    
    def _resolve_entity_path(
        self, 
        entity_id: EntityId, 
        state: Optional[str] = None,
    ) -> Path:
        """Resolve path for a QA record file in global directory."""
        filename = self._get_entity_filename(entity_id)
        if state:
            return self._get_state_dir(state) / filename
        return self._get_state_dir("waiting") / filename
    
    def _get_entity_filename(self, entity_id: EntityId) -> str:
        """Generate filename for a QA record."""
        return f"{entity_id}{self.file_extension}"

    def _find_entity_path(self, entity_id: EntityId) -> Optional[Path]:
        """Find path for a QA record, checking global and session directories.

        Uses SessionScopedMixin for unified search across global and session dirs.
        """
        return self._find_entity_path_with_sessions(entity_id)

    def _resolve_session_qa_path(self, qa_id: str, session_id: str, state: str) -> Path:
        """Resolve path for a QA record in a session directory.

        Uses SessionScopedMixin for session path resolution.
        """
        return self._resolve_session_record_path(qa_id, session_id, state)
    
    # ---------- CRUD Implementation ----------
    
    def _do_create(self, entity: QARecord) -> QARecord:
        """Create a new QA record file."""
        if entity.session_id:
            path = self._resolve_session_qa_path(entity.id, entity.session_id, entity.state)
        else:
            path = self._resolve_entity_path(entity.id, entity.state)
            
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._qa_to_markdown(entity)
        path.write_text(content, encoding="utf-8")
        return entity
    
    def _do_get(self, entity_id: EntityId) -> Optional[QARecord]:
        """Get a QA record by ID."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return None
        return self._load_qa_from_file(path)
    
    def _do_save(self, entity: QARecord) -> None:
        """Save a QA record."""
        current_path = self._find_entity_path(entity.id)
        
        if entity.session_id:
            target_path = self._resolve_session_qa_path(entity.id, entity.session_id, entity.state)
        else:
            target_path = self._resolve_entity_path(entity.id, entity.state)
        
        if current_path is None:
            self._do_create(entity)
            return
        
        if current_path.resolve() != target_path.resolve():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                current_path.rename(target_path)
            except OSError:
                content = self._qa_to_markdown(entity)
                target_path.write_text(content, encoding="utf-8")
                current_path.unlink()
        
        content = self._qa_to_markdown(entity)
        target_path.write_text(content, encoding="utf-8")
    
    def _do_delete(self, entity_id: EntityId) -> bool:
        """Delete a QA record."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return False
        path.unlink()
        return True
    
    def _do_exists(self, entity_id: EntityId) -> bool:
        """Check if a QA record exists."""
        return self._find_entity_path(entity_id) is not None

    # ---------- Workflow Methods ----------

    def advance_state(self, qa_id: str, new_state: str, session_id: Optional[str] = None) -> QARecord:
        """Advance QA record to a new state.
        
        This is a HIGH-LEVEL workflow method that moves QA between states.
        
        Args:
            qa_id: QA record identifier
            new_state: Target state (from config)
            session_id: Optional session context to update ownership
            
        Returns:
            Updated QA record
            
        Raises:
            PersistenceError: If QA not found
        """
        qa = self.get(qa_id)
        if not qa:
            raise PersistenceError(f"QA record not found: {qa_id}")
            
        old_state = qa.state
        qa.state = new_state
        
        if session_id:
            qa.session_id = session_id
            
        qa.record_transition(old_state, new_state, reason="workflow_advance")
        
        self.save(qa)
        
        return qa
    
    # ---------- Query Implementation ----------

    def _do_list_by_state(self, state: str) -> List[QARecord]:
        """List QA records in a given state."""
        state_dir = self._get_state_dir(state)
        if not state_dir.exists():
            return []
        
        records: List[QARecord] = []
        for path in state_dir.glob(f"*{self.file_extension}"):
            qa = self._load_qa_from_file(path)
            if qa:
                records.append(qa)
        return records
    
    def _do_list_all(self) -> List[QARecord]:
        """List all QA records."""
        records: List[QARecord] = []
        for state in self._get_states_to_search():
            records.extend(self._do_list_by_state(state))
        return records
    
    # ---------- QA-specific Methods ----------
    
    def find_by_task(self, task_id: str) -> List[QARecord]:
        """Find QA records for a task."""
        return self._do_find(task_id=task_id)
    
    def find_by_session(self, session_id: str) -> List[QARecord]:
        """Find QA records belonging to a session."""
        return self._do_find(session_id=session_id)
    
    # ---------- File Format Helpers ----------

    def _qa_to_markdown(self, qa: QARecord) -> str:
        """Convert QA record to markdown format.

        Uses format_html_comment from utils/text for consistent metadata formatting.
        """
        import json
        lines: List[str] = []

        # Metadata comments using shared utility
        lines.append(format_html_comment("Task", qa.task_id))
        lines.append(format_html_comment("Status", qa.state))
        if qa.session_id:
            lines.append(format_html_comment("Session", qa.session_id))
        lines.append(format_html_comment("Round", qa.round))
        if qa.metadata.created_by:
            lines.append(format_html_comment("Validator", qa.metadata.created_by))

        # Persist metadata timestamps
        lines.append(format_html_comment("CreatedAt", qa.metadata.created_at))
        lines.append(format_html_comment("UpdatedAt", qa.metadata.updated_at))

        # Persist state history as JSON in a comment
        if qa.state_history:
            history_data = [h.to_dict() for h in qa.state_history]
            history_json = json.dumps(history_data)
            lines.append(format_html_comment("StateHistory", history_json))

        lines.append("")
        lines.append(f"# {qa.title}")
        return "\n".join(lines)

    def _load_qa_from_file(self, path: Path) -> Optional[QARecord]:
        """Load a QA record from a markdown file."""
        try:
            content = path.read_text(encoding="utf-8")
            return self._parse_qa_markdown(path.stem, content, path)
        except Exception:
            return None

    def _parse_qa_markdown(
        self,
        qa_id: str,
        content: str,
        path: Path,
    ) -> QARecord:
        """Parse QA record from markdown content.

        Uses parse_html_comment and parse_title from utils/text for consistent parsing.
        """
        import json
        from edison.core.entity import StateHistoryEntry

        task_id = ""
        state = path.parent.name
        session_id = None
        round_num = 1
        title = ""
        validator = None
        created_at = None
        updated_at = None
        state_history: List[StateHistoryEntry] = []

        for line in content.split("\n"):
            # Use shared utilities for parsing
            if parsed := parse_html_comment(line, "Task"):
                task_id = parsed
            elif parsed := parse_html_comment(line, "Status"):
                state = parsed
            elif parsed := parse_html_comment(line, "Session"):
                session_id = parsed
            elif parsed := parse_html_comment(line, "Round"):
                try:
                    round_num = int(parsed)
                except ValueError:
                    pass
            elif parsed := parse_html_comment(line, "Validator"):
                validator = parsed
            elif parsed := parse_html_comment(line, "CreatedAt"):
                created_at = parsed
            elif parsed := parse_html_comment(line, "UpdatedAt"):
                updated_at = parsed
            elif parsed := parse_html_comment(line, "StateHistory"):
                try:
                    history_data = json.loads(parsed)
                    state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
                except (ValueError, json.JSONDecodeError):
                    pass
            elif not title and (parsed := parse_title(line)):
                title = parsed

        # Build metadata with persisted timestamps if available
        if created_at and updated_at:
            metadata = EntityMetadata(
                created_at=created_at,
                updated_at=updated_at,
                created_by=validator,
                session_id=session_id,
            )
        else:
            metadata = EntityMetadata.create(created_by=validator, session_id=session_id)

        return QARecord(
            id=qa_id,
            task_id=task_id,
            state=state,
            title=title,
            session_id=session_id,
            metadata=metadata,
            state_history=state_history,
            round=round_num,
        )


__all__ = [
    "QARepository",
]
