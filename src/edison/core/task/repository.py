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
from edison.core.utils.text import parse_frontmatter, format_frontmatter, has_frontmatter, parse_title
from edison.core.config.domains import TaskConfig
from edison.core.utils.time import utc_timestamp

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

        # Strict load for direct lookup: if a file exists but is legacy/unparseable,
        # surface an actionable error instead of pretending the task doesn't exist.
        content = path.read_text(encoding="utf-8", errors="strict")
        if not has_frontmatter(content):
            raise PersistenceError(
                f"Task file at {path} is missing YAML frontmatter. "
                "Restore the file from TEMPLATE.md or recreate the task via `edison task new`."
            )

        try:
            return self._parse_task_markdown(path.stem, content, path)
        except Exception as exc:
            raise PersistenceError(f"Failed to parse task file at {path}: {exc}") from exc
    
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

    # ---------- Extended Query Methods ----------

    def find_by_state(self, state: str) -> List[Task]:
        """Find all tasks in a given state across all directories.

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
        """Find all tasks across all states.

        Searches both global and session directories.

        Returns:
            List of all tasks
        """
        return self._do_list_all()

    def get_next_child_id(self, parent_id: str) -> str:
        """Get the next available child ID for a parent task.

        Scans task directories to find existing children of the parent
        and returns the next sequential child ID.

        Args:
            parent_id: Parent task ID (e.g., "201" or "201-wave1-something")

        Returns:
            Next child ID (e.g., "201.1" or "201.2")
        """
        existing_children: List[int] = []

        # Get all tasks and find children of this parent
        all_tasks = self._do_list_all()
        for task in all_tasks:
            # Check if task ID starts with parent_id followed by a dot (child pattern)
            if task.id.startswith(f"{parent_id}."):
                # Extract child number from "201.1-something" or "201.1"
                suffix = task.id[len(parent_id) + 1:]  # After "parent_id."
                parts = suffix.split("-", 1)
                if parts[0].isdigit():
                    existing_children.append(int(parts[0]))

        # Also scan raw file names for any not yet loaded as Task objects
        for state in self._get_states_to_search():
            state_dir = self._get_tasks_root() / state
            if state_dir.exists():
                for path in state_dir.glob(f"{parent_id}.*{self.file_extension}"):
                    # Extract child number from filename
                    name_part = path.stem.split("-")[0]  # Get "201.1" part
                    if "." in name_part:
                        try:
                            child_num = int(name_part.split(".")[-1])
                            if child_num not in existing_children:
                                existing_children.append(child_num)
                        except ValueError:
                            pass

        # Determine next child number
        next_child_num = max(existing_children) + 1 if existing_children else 1
        return f"{parent_id}.{next_child_num}"

    def get_next_top_level_id(self) -> int:
        """Get the next available top-level task ID number.

        Scans all tasks to find the highest numeric prefix and returns next.

        Returns:
            Next top-level ID number (e.g., 151 if highest is 150)
        """
        max_id = 0
        for task in self._do_list_all():
            # Extract numeric prefix from IDs like "150-something"
            parts = task.id.split("-")
            if parts[0].isdigit():
                max_id = max(max_id, int(parts[0]))
        return max_id + 1

    # ---------- File Format Helpers ----------

    def _task_to_markdown(self, task: Task) -> str:
        """Convert task to markdown format with YAML frontmatter.

        State is NOT stored in the frontmatter - it's derived from the directory.
        All other task metadata is stored in YAML frontmatter for single source of truth.
        """
        # Build frontmatter data (exclude None values)
        frontmatter_data: Dict[str, Any] = {
            "id": task.id,
            "title": task.title,
            "owner": task.metadata.created_by,
            "session_id": task.session_id,
            "parent_id": task.parent_id,
            "child_ids": task.child_ids if task.child_ids else None,
            "depends_on": task.depends_on if task.depends_on else None,
            "blocks_tasks": task.blocks_tasks if task.blocks_tasks else None,
            "claimed_at": task.claimed_at,
            "last_active": task.last_active,
            "continuation_id": task.continuation_id,
            "delegated_to": task.delegated_to,
            "delegated_in_session": task.delegated_in_session,
            "created_at": task.metadata.created_at,
            "updated_at": task.metadata.updated_at,
            "tags": task.tags if task.tags else None,
        }

        # Format as YAML frontmatter
        yaml_header = format_frontmatter(frontmatter_data, exclude_none=True)

        # Build markdown body
        body_lines: List[str] = [
            f"# {task.title}",
            "",
        ]

        if task.description:
            body_lines.append(task.description)

        return yaml_header + "\n".join(body_lines)

    def _load_task_from_file(self, path: Path) -> Optional[Task]:
        """Load a task from a markdown file."""
        # Tolerant load for directory scans/listings: ignore non-task files and
        # skip legacy/unparseable content without failing the whole listing.
        try:
            # Fast path: YAML frontmatter always starts with `---` at the very beginning.
            # Avoid reading whole legacy files just to discover they aren't v2 tasks.
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                prefix = f.read(3)
                if prefix != "---":
                    return None
                content = prefix + f.read()

            if not has_frontmatter(content):
                return None
            return self._parse_task_markdown(path.stem, content, path)
        except Exception:
            return None

    def _parse_task_markdown(
        self,
        task_id: str,
        content: str,
        path: Path,
    ) -> Task:
        """Parse task from markdown content with YAML frontmatter.

        State is ALWAYS derived from directory location, never from file content.

        Args:
            task_id: Task ID from filename
            content: Markdown content with YAML frontmatter
            path: File path (for state derivation)

        Returns:
            Task instance
            
        Raises:
            ValueError: If content does not have valid YAML frontmatter
        """
        # State is ALWAYS derived from directory - single source of truth
        state = path.parent.name

        # Parse YAML frontmatter (only supported format)
        if not has_frontmatter(content):
            raise ValueError(
                f"Task {task_id} does not have YAML frontmatter."
            )

        doc = parse_frontmatter(content)
        fm = doc.frontmatter

        # Extract title from frontmatter or markdown heading
        title = fm.get("title", "")
        if not title:
            # Try to find title in markdown content
            for line in doc.content.split("\n"):
                if parsed := parse_title(line):
                    title = parsed
                    break

        # Extract description from markdown body (after title)
        description_lines: List[str] = []
        found_title = False
        for line in doc.content.split("\n"):
            if not found_title and parse_title(line):
                found_title = True
                continue
            if found_title:
                description_lines.append(line)
        description = "\n".join(description_lines).strip()

        # Build metadata
        metadata = EntityMetadata(
            created_at=fm.get("created_at", ""),
            updated_at=fm.get("updated_at", ""),
            created_by=fm.get("owner"),
            session_id=fm.get("session_id"),
        )

        return Task(
            id=fm.get("id", task_id),
            state=state,  # Always from directory
            title=title,
            description=description,
            session_id=fm.get("session_id"),
            metadata=metadata,
            tags=fm.get("tags", []) or [],
            parent_id=fm.get("parent_id"),
            child_ids=fm.get("child_ids", []) or [],
            depends_on=fm.get("depends_on", []) or [],
            blocks_tasks=fm.get("blocks_tasks", []) or [],
            claimed_at=fm.get("claimed_at"),
            last_active=fm.get("last_active"),
            continuation_id=fm.get("continuation_id"),
            delegated_to=fm.get("delegated_to"),
            delegated_in_session=fm.get("delegated_in_session"),
        )


__all__ = [
    "TaskRepository",
]
