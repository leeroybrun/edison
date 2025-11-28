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
    SessionScopedMixin,
    EntityId,
    EntityMetadata,
    PersistenceError,
)
from edison.core.utils.paths import PathResolver
from edison.core.utils.text import parse_html_comment, format_html_comment, parse_title
from edison.core.config.domains import TaskConfig

from .models import Task


class TaskRepository(
    BaseRepository[Task],
    FileRepositoryMixin[Task],
    SessionScopedMixin[Task],
):
    """File-based repository for task entities.

    Tasks are stored as Markdown files in state-based directories:
    - .project/tasks/todo/
    - .project/tasks/wip/
    - .project/tasks/done/
    - .project/tasks/validated/

    Supports session-scoped storage via SessionScopedMixin.
    """

    entity_type: str = "task"
    file_extension: str = ".md"

    # SessionScopedMixin configuration
    record_type: str = "task"
    record_subdir: str = "tasks"

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
        """Get list of states to search from configuration.

        Returns:
            List of task state names

        Raises:
            ValueError: If config doesn't provide task states
        """
        states = self._config.task_states()
        if not states:
            raise ValueError("Configuration must define task states (statemachine.task.states)")
        return states
    
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

    def _find_entity_path(self, entity_id: EntityId) -> Optional[Path]:
        """Find path for a task, checking global and session directories.

        Uses SessionScopedMixin for unified search across global and session dirs.
        """
        return self._find_entity_path_with_sessions(entity_id)

    def _resolve_session_task_path(self, task_id: str, session_id: str, state: str) -> Path:
        """Resolve path for a task in a session directory.

        Uses SessionScopedMixin for session path resolution.
        """
        return self._resolve_session_record_path(task_id, session_id, state)

    # ---------- CRUD Implementation ----------
    
    def _do_create(self, entity: Task) -> Task:
        """Create a new task file."""
        if entity.session_id:
            path = self._resolve_session_task_path(entity.id, entity.session_id, entity.state)
        else:
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
        
        # Determine target path
        if entity.session_id:
            target_path = self._resolve_session_task_path(entity.id, entity.session_id, entity.state)
        else:
            target_path = self._resolve_entity_path(entity.id, entity.state)
        
        if current_path is None:
            # New task - create it
            self._do_create(entity)
            return
        
        # Check if state or location changed (need to move file)
        if current_path.resolve() != target_path.resolve():
            # Move to new state directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # We copy content first then unlink to be safe(r) or use rename
            # rename is atomic on same filesystem
            try:
                current_path.rename(target_path)
            except OSError:
                # Cross-device move?
                content = self._task_to_markdown(entity)
                target_path.write_text(content, encoding="utf-8")
                current_path.unlink()
        
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
        """List all tasks from global and session directories."""
        tasks: List[Task] = []
        
        # 1. Global tasks
        for state in self._get_states_to_search():
            tasks.extend(self._do_list_by_state(state))
            
        # 2. Session tasks
        for base in self._get_session_bases():
            for state in self._get_states_to_search():
                # Session structure: {base}/tasks/{state}/
                state_dir = base / "tasks" / state
                if state_dir.exists():
                    for path in state_dir.glob(f"*{self.file_extension}"):
                        task = self._load_task_from_file(path)
                        if task:
                            tasks.append(task)
                            
        return tasks
    
    # ---------- Task-specific Methods ----------

    def find_by_session(self, session_id: str) -> List[Task]:
        """Find tasks belonging to a session."""
        return self._do_find(session_id=session_id)

    # ---------- Finder-compatible Methods ----------

    def find_by_state(self, state: str) -> List[Task]:
        """Find all tasks in a given state (alias for list_by_state).

        This method provides compatibility with the legacy finder.py module.
        Searches both global and session directories.

        Args:
            state: Task state to filter by

        Returns:
            List of tasks in the given state
        """
        # Search global state directory
        tasks = self._do_list_by_state(state)

        # Search session directories
        for base in self._get_session_bases():
            state_dir = base / "tasks" / state
            if state_dir.exists():
                for path in state_dir.glob(f"*{self.file_extension}"):
                    task = self._load_task_from_file(path)
                    if task:
                        tasks.append(task)

        return tasks

    def find_all(self) -> List[Task]:
        """Find all tasks across all states (alias for list_all).

        This method provides compatibility with the legacy finder.py module.
        Searches both global and session directories.

        Returns:
            List of all tasks
        """
        return self._do_list_all()
    
    # ---------- File Format Helpers ----------

    def _task_to_markdown(self, task: Task) -> str:
        """Convert task to markdown format.

        Uses format_html_comment from utils/text for consistent metadata formatting.
        """
        lines: List[str] = []

        # Metadata comments using shared utility
        if task.metadata.created_by:
            lines.append(format_html_comment("Owner", task.metadata.created_by))
        lines.append(format_html_comment("Status", task.state))
        if task.session_id:
            lines.append(format_html_comment("Session", task.session_id))

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

        Uses parse_html_comment and parse_title from utils/text for consistent parsing.

        Args:
            task_id: Task ID from filename
            content: Markdown content
            path: File path (for state inference)

        Returns:
            Task instance
        """
        owner = None
        state = None
        session_id = None
        title = ""
        description_lines: List[str] = []
        in_description = False

        for line in content.split("\n"):
            # Use shared utilities for parsing
            if parsed := parse_html_comment(line, "Owner"):
                owner = parsed
            elif parsed := parse_html_comment(line, "Status"):
                state = parsed
            elif parsed := parse_html_comment(line, "Session"):
                session_id = parsed
            elif not title and (parsed := parse_title(line)):
                title = parsed
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


__all__ = [
    "TaskRepository",
]


