"""TaskManager facade for task operations.

This module provides a manager class that wraps the TaskRepository
with higher-level business logic for task operations.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from edison.core.utils.paths import PathResolver
from edison.core.entity import EntityNotFoundError, EntityStateError

from .config import TaskConfig
from .models import Task
from .repository import TaskRepository


class TaskManager:
    """Manager for task operations with repository pattern.
    
    Provides a high-level API for task management including:
    - Creating tasks
    - Claiming tasks for sessions
    - Transitioning task states
    - Querying tasks
    
    Uses TaskRepository for persistence.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize task manager.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
        self._repo = TaskRepository(project_root=self.project_root)

    def create_task(
        self, 
        task_id: str, 
        title: str,
        *,
        description: str = "",
        session_id: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> Task:
        """Create a new task.
        
        Args:
            task_id: Task identifier
            title: Task title
            description: Task description
            session_id: Associated session
            owner: Task owner
            
        Returns:
            Created task
        """
        task = Task.create(
            task_id=task_id,
            title=title,
            description=description,
            session_id=session_id,
            owner=owner,
        )
        return self._repo.create(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task if found, None otherwise
        """
        return self._repo.get(task_id)

    def claim_task(self, task_id: str, session_id: str) -> Path:
        """Claim a task for a session.
        
        Moves the task from todo to wip and associates it with the session.
        Uses the legacy file-based approach for compatibility.
        
        Args:
            task_id: Task identifier
            session_id: Session to claim for
            
        Returns:
            Path to the claimed task file
            
        Raises:
            FileNotFoundError: If task not found
        """
        # Use legacy io.claim_task for backward compatibility
        from .io import claim_task as legacy_claim_task
        
        src, dest = legacy_claim_task(task_id, session_id)
        return dest

    def transition_task(
        self, 
        task_id: str, 
        status: str, 
        *, 
        session_id: Optional[str] = None
    ) -> Path:
        """Transition a task to a new state.

        The status must be allowed by the configured task state machine.
        Uses the legacy file-based approach for compatibility.
        
        Args:
            task_id: Task identifier
            status: Target state
            session_id: Optional session context
            
        Returns:
            Path to the transitioned task file
            
        Raises:
            ValueError: If status is not valid
            FileNotFoundError: If task not found
        """
        import edison.core.task as task_module
        
        cfg = self._config
        allowed = {s.lower() for s in cfg.task_states()}
        target = status.lower()
        if target not in allowed:
            raise ValueError(f"Unknown status '{status}'")

        src = task_module.find_record(task_id, "task", session_id=session_id)
        dest = task_module.move_to_status(src, "task", target, session_id=session_id)

        # Keep status line in sync for human readability
        try:
            text = dest.read_text(encoding="utf-8")
        except Exception:
            text = ""

        lines = text.splitlines() if text else []
        wrote = False
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith("status:"):
                lines[idx] = f"status: {target}"
                wrote = True
                break
        if not wrote:
            lines.append(f"status: {target}")
        dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return dest

    def list_tasks(self, state: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered by state.
        
        Args:
            state: State to filter by (optional)
            
        Returns:
            List of tasks
        """
        if state:
            return self._repo.list_by_state(state)
        return self._repo.list_all()

    def find_tasks_by_session(self, session_id: str) -> List[Task]:
        """Find tasks belonging to a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of tasks in the session
        """
        return self._repo.find_by_session(session_id)



__all__ = ["TaskManager"]
