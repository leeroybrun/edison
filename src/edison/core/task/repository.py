"""Task repository for file-based persistence.

This module provides the TaskRepository class that implements
the repository pattern for task entities.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    BaseRepository,
    FileRepositoryMixin,
    EntityId,
    PersistenceError,
)
from edison.core.utils.paths import PathResolver

from .models import Task, QARecord
from .config import TaskConfig


class TaskRepository(BaseRepository[Task], FileRepositoryMixin[Task]):
    """File-based repository for task entities.
    
    Tasks are stored as Markdown files in state-based directories:
    - .project/tasks/todo/
    - .project/tasks/wip/
    - .project/tasks/done/
    - .project/tasks/validated/
    """
    
    entity_type: str = "task"
    file_extension: str = ".md"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize repository.
        
        Args:
            project_root: Project root directory
        """
        super().__init__(project_root)
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
    
    # ---------- Path Resolution ----------
    
    def _get_tasks_root(self) -> Path:
        """Get the tasks root directory."""
        return self._config.tasks_root()
    
    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a task state."""
        return self._get_tasks_root() / state
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search."""
        return self._config.task_states() or ["todo", "wip", "blocked", "done", "validated"]
    
    def _resolve_entity_path(
        self, 
        entity_id: EntityId, 
        state: Optional[str] = None,
    ) -> Path:
        """Resolve path for a task file.
        
        Args:
            entity_id: Task identifier
            state: Task state (for state-based directories)
            
        Returns:
            Path to task file
        """
        filename = self._get_entity_filename(entity_id)
        if state:
            return self._get_state_dir(state) / filename
        # Default to todo
        return self._get_state_dir("todo") / filename
    
    def _get_entity_filename(self, entity_id: EntityId) -> str:
        """Generate filename for a task."""
        return f"{entity_id}{self.file_extension}"
    
    # ---------- CRUD Implementation ----------
    
    def _do_create(self, entity: Task) -> Task:
        """Create a new task file."""
        path = self._resolve_entity_path(entity.id, entity.state)
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write task as markdown
        content = self._task_to_markdown(entity)
        path.write_text(content, encoding="utf-8")
        
        return entity
    
    def _do_get(self, entity_id: EntityId) -> Optional[Task]:
        """Get a task by ID."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return None
        
        return self._load_task_from_file(path)
    
    def _do_save(self, entity: Task) -> None:
        """Save a task."""
        # Find current location
        current_path = self._find_entity_path(entity.id)
        target_path = self._resolve_entity_path(entity.id, entity.state)
        
        if current_path is None:
            # New task - create it
            self._do_create(entity)
            return
        
        # Check if state changed (need to move file)
        if current_path != target_path:
            # Move to new state directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            current_path.rename(target_path)
        
        # Write updated content
        content = self._task_to_markdown(entity)
        target_path.write_text(content, encoding="utf-8")
    
    def _do_delete(self, entity_id: EntityId) -> bool:
        """Delete a task."""
        path = self._find_entity_path(entity_id)
        if path is None:
            return False
        
        path.unlink()
        return True
    
    def _do_exists(self, entity_id: EntityId) -> bool:
        """Check if a task exists."""
        return self._find_entity_path(entity_id) is not None
    
    # ---------- Query Implementation ----------
    
    def _do_find(self, **criteria: Any) -> List[Task]:
        """Find tasks matching criteria."""
        results: List[Task] = []
        
        for task in self._do_list_all():
            match = True
            for key, value in criteria.items():
                task_value = getattr(task, key, None)
                if task_value != value:
                    match = False
                    break
            if match:
                results.append(task)
        
        return results
    
    def _do_list_by_state(self, state: str) -> List[Task]:
        """List tasks in a given state."""
        state_dir = self._get_state_dir(state)
        if not state_dir.exists():
            return []
        
        tasks: List[Task] = []
        for path in state_dir.glob(f"*{self.file_extension}"):
            task = self._load_task_from_file(path)
            if task:
                tasks.append(task)
        
        return tasks
    
    def _do_list_all(self) -> List[Task]:
        """List all tasks."""
        tasks: List[Task] = []
        for state in self._get_states_to_search():
            tasks.extend(self._do_list_by_state(state))
        return tasks
    
    # ---------- Task-specific Methods ----------
    
    def find_by_session(self, session_id: str) -> List[Task]:
        """Find tasks belonging to a session."""
        return self._do_find(session_id=session_id)
    
    # ---------- File Format Helpers ----------
    
    def _task_to_markdown(self, task: Task) -> str:
        """Convert task to markdown format.
        
        Format:
        ```
        <!-- Owner: {owner} -->
        <!-- Status: {state} -->
        <!-- Session: {session_id} -->
        
        # {title}
        
        {description}
        ```
        """
        lines: List[str] = []
        
        # Metadata comments
        if task.metadata.created_by:
            lines.append(f"<!-- Owner: {task.metadata.created_by} -->")
        lines.append(f"<!-- Status: {task.state} -->")
        if task.session_id:
            lines.append(f"<!-- Session: {task.session_id} -->")
        
        lines.append("")
        lines.append(f"# {task.title}")
        lines.append("")
        
        if task.description:
            lines.append(task.description)
        
        return "\n".join(lines)
    
    def _load_task_from_file(self, path: Path) -> Optional[Task]:
        """Load a task from a markdown file."""
        try:
            content = path.read_text(encoding="utf-8")
            return self._parse_task_markdown(path.stem, content, path)
        except Exception:
            return None
    
    def _parse_task_markdown(
        self, 
        task_id: str, 
        content: str,
        path: Path,
    ) -> Task:
        """Parse task from markdown content.
        
        Args:
            task_id: Task ID from filename
            content: Markdown content
            path: File path (for state inference)
            
        Returns:
            Task instance
        """
        # Extract metadata from HTML comments
        owner = None
        state = None
        session_id = None
        title = ""
        description_lines: List[str] = []
        in_description = False
        
        for line in content.split("\n"):
            stripped = line.strip()
            
            # Parse metadata comments
            if stripped.startswith("<!-- Owner:") and stripped.endswith("-->"):
                owner = stripped[11:-3].strip()
            elif stripped.startswith("<!-- Status:") and stripped.endswith("-->"):
                state = stripped[12:-3].strip()
            elif stripped.startswith("<!-- Session:") and stripped.endswith("-->"):
                session_id = stripped[13:-3].strip()
            elif stripped.startswith("# ") and not title:
                title = stripped[2:].strip()
                in_description = True
            elif in_description:
                description_lines.append(line)
        
        # Infer state from path if not in content
        if not state:
            state = path.parent.name
        
        description = "\n".join(description_lines).strip()
        
        return Task(
            id=task_id,
            state=state,
            title=title,
            description=description,
            session_id=session_id,
            metadata=EntityMetadata.create(created_by=owner, session_id=session_id),
        )


class QARepository(BaseRepository[QARecord], FileRepositoryMixin[QARecord]):
    """File-based repository for QA record entities."""
    
    entity_type: str = "qa"
    file_extension: str = ".md"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        super().__init__(project_root)
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
    
    def _get_qa_root(self) -> Path:
        """Get the QA root directory."""
        return self._config.qa_root()
    
    def _get_state_dir(self, state: str) -> Path:
        """Get directory for a QA state."""
        return self._get_qa_root() / state
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search."""
        return self._config.qa_states() or ["waiting", "todo", "wip", "done", "validated"]
    
    def _resolve_entity_path(
        self, 
        entity_id: EntityId, 
        state: Optional[str] = None,
    ) -> Path:
        filename = self._get_entity_filename(entity_id)
        if state:
            return self._get_state_dir(state) / filename
        return self._get_state_dir("waiting") / filename
    
    def _do_create(self, entity: QARecord) -> QARecord:
        path = self._resolve_entity_path(entity.id, entity.state)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self._qa_to_markdown(entity)
        path.write_text(content, encoding="utf-8")
        return entity
    
    def _do_get(self, entity_id: EntityId) -> Optional[QARecord]:
        path = self._find_entity_path(entity_id)
        if path is None:
            return None
        return self._load_qa_from_file(path)
    
    def _do_save(self, entity: QARecord) -> None:
        current_path = self._find_entity_path(entity.id)
        target_path = self._resolve_entity_path(entity.id, entity.state)
        
        if current_path is None:
            self._do_create(entity)
            return
        
        if current_path != target_path:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            current_path.rename(target_path)
        
        content = self._qa_to_markdown(entity)
        target_path.write_text(content, encoding="utf-8")
    
    def _do_delete(self, entity_id: EntityId) -> bool:
        path = self._find_entity_path(entity_id)
        if path is None:
            return False
        path.unlink()
        return True
    
    def _do_exists(self, entity_id: EntityId) -> bool:
        return self._find_entity_path(entity_id) is not None
    
    def _do_find(self, **criteria: Any) -> List[QARecord]:
        results: List[QARecord] = []
        for qa in self._do_list_all():
            match = all(getattr(qa, k, None) == v for k, v in criteria.items())
            if match:
                results.append(qa)
        return results
    
    def _do_list_by_state(self, state: str) -> List[QARecord]:
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
        records: List[QARecord] = []
        for state in self._get_states_to_search():
            records.extend(self._do_list_by_state(state))
        return records
    
    def find_by_task(self, task_id: str) -> List[QARecord]:
        """Find QA records for a task."""
        return self._do_find(task_id=task_id)
    
    def _qa_to_markdown(self, qa: QARecord) -> str:
        lines: List[str] = []
        lines.append(f"<!-- Task: {qa.task_id} -->")
        lines.append(f"<!-- Status: {qa.state} -->")
        if qa.session_id:
            lines.append(f"<!-- Session: {qa.session_id} -->")
        lines.append(f"<!-- Round: {qa.round} -->")
        lines.append("")
        lines.append(f"# {qa.title}")
        return "\n".join(lines)
    
    def _load_qa_from_file(self, path: Path) -> Optional[QARecord]:
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
        task_id = ""
        state = path.parent.name
        session_id = None
        round_num = 1
        title = ""
        
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("<!-- Task:") and stripped.endswith("-->"):
                task_id = stripped[10:-3].strip()
            elif stripped.startswith("<!-- Status:") and stripped.endswith("-->"):
                state = stripped[12:-3].strip()
            elif stripped.startswith("<!-- Session:") and stripped.endswith("-->"):
                session_id = stripped[13:-3].strip()
            elif stripped.startswith("<!-- Round:") and stripped.endswith("-->"):
                try:
                    round_num = int(stripped[11:-3].strip())
                except ValueError:
                    pass
            elif stripped.startswith("# ") and not title:
                title = stripped[2:].strip()
        
        return QARecord(
            id=qa_id,
            task_id=task_id,
            state=state,
            title=title,
            session_id=session_id,
            round=round_num,
        )


# Import EntityMetadata at module level to avoid issues in _parse_task_markdown
from edison.core.entity import EntityMetadata


__all__ = [
    "TaskRepository",
    "QARepository",
]


