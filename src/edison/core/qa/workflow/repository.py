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
from edison.core.utils.text import parse_frontmatter, format_frontmatter, has_frontmatter, parse_title
from edison.core.config.domains import TaskConfig

from ..models import QARecord
from .._utils import get_qa_root_path
import json


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
        self._qa_root = get_qa_root_path(self.project_root)

    # ---------- Path Resolution ----------

    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a QA state."""
        return self._qa_root / state
    
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
        """Advance QA record to a new state using proper state machine validation.
        
        This is a HIGH-LEVEL workflow method that moves QA between states.
        Uses transition_entity() to ensure guards and actions are executed.
        
        Args:
            qa_id: QA record identifier
            new_state: Target state (from config)
            session_id: Optional session context to update ownership
            
        Returns:
            Updated QA record
            
        Raises:
            PersistenceError: If QA not found or transition not allowed
        """
        from edison.core.state.transitions import transition_entity, EntityTransitionError
        from edison.core.entity import StateHistoryEntry
        
        qa = self.get(qa_id)
        if not qa:
            raise PersistenceError(f"QA record not found: {qa_id}")
            
        old_state = qa.state
        
        # Use transition_entity to validate guards and execute actions
        try:
            result = transition_entity(
                entity_type="qa",
                entity_id=qa_id,
                to_state=new_state,
                current_state=old_state,
                context={
                    "qa": {"id": qa_id, "task_id": qa.task_id, "state": old_state},
                    "session": {"id": session_id} if session_id else {},
                    "session_id": session_id,
                },
            )
            
            # Update QA with transition result
            qa.state = result["state"]
            if session_id:
                qa.session_id = session_id
            if "history_entry" in result:
                entry = StateHistoryEntry.from_dict(result["history_entry"])
                qa.state_history.append(entry)
                
        except EntityTransitionError as e:
            raise PersistenceError(f"Transition not allowed: {e}") from e
        
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
        """Convert QA record to markdown format with YAML frontmatter.

        State is NOT stored in the frontmatter - it's derived from the directory.
        All other QA metadata is stored in YAML frontmatter for single source of truth.
        """
        from typing import Any, Dict

        # Build state history as serializable list
        state_history_data = None
        if qa.state_history:
            state_history_data = [h.to_dict() for h in qa.state_history]

        # Build frontmatter data (exclude None values)
        frontmatter_data: Dict[str, Any] = {
            "id": qa.id,
            "task_id": qa.task_id,
            "title": qa.title,
            "round": qa.round,
            "validator_owner": qa.validator_owner or qa.metadata.created_by,
            "session_id": qa.session_id,
            "validators": qa.validators if qa.validators else None,
            "evidence": qa.evidence if qa.evidence else None,
            "created_at": qa.metadata.created_at,
            "updated_at": qa.metadata.updated_at,
            "state_history": state_history_data,
        }

        # Format as YAML frontmatter
        yaml_header = format_frontmatter(frontmatter_data, exclude_none=True)

        # Build markdown body
        body_lines: List[str] = [
            f"# {qa.title}",
            "",
        ]

        return yaml_header + "\n".join(body_lines)

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
        """Parse QA record from markdown content with YAML frontmatter.

        State is ALWAYS derived from directory location, never from file content.
        
        NOTE: Only YAML frontmatter format is supported. Legacy HTML comment
        format must be migrated using `edison migrate task_frontmatter`.

        Args:
            qa_id: QA ID from filename
            content: Markdown content with YAML frontmatter
            path: File path (for state derivation)

        Returns:
            QARecord instance
            
        Raises:
            ValueError: If content does not have valid YAML frontmatter
        """
        from edison.core.entity import StateHistoryEntry

        # State is ALWAYS derived from directory - single source of truth
        state = path.parent.name

        # Parse YAML frontmatter (only supported format)
        if not has_frontmatter(content):
            raise ValueError(
                f"QA record {qa_id} does not have YAML frontmatter. "
                "Run `edison migrate task_frontmatter` to convert legacy files."
            )

        doc = parse_frontmatter(content)
        fm = doc.frontmatter

        # Extract title from frontmatter or markdown heading
        title = fm.get("title", "")
        if not title:
            for line in doc.content.split("\n"):
                if parsed := parse_title(line):
                    title = parsed
                    break

        # Build state history from frontmatter
        state_history: List = []
        history_data = fm.get("state_history", [])
        if history_data:
            state_history = [StateHistoryEntry.from_dict(h) for h in history_data]

        # Build metadata
        metadata = EntityMetadata(
            created_at=fm.get("created_at", ""),
            updated_at=fm.get("updated_at", ""),
            created_by=fm.get("validator_owner"),
            session_id=fm.get("session_id"),
        )

        return QARecord(
            id=fm.get("id", qa_id),
            task_id=fm.get("task_id", ""),
            state=state,  # Always from directory
            title=title,
            session_id=fm.get("session_id"),
            validator_owner=fm.get("validator_owner"),
            metadata=metadata,
            state_history=state_history,
            validators=fm.get("validators", []) or [],
            evidence=fm.get("evidence", []) or [],
            round=fm.get("round", 1),
        )


__all__ = [
    "QARepository",
]
