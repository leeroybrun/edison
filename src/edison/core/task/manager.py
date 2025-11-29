"""TaskManager facade for task operations.

This module provides a manager class that wraps the TaskRepository
with higher-level business logic for task operations.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from edison.core.utils.paths import PathResolver
from edison.core.config.domains import TaskConfig

from .models import Task
from .repository import TaskRepository
from .workflow import TaskQAWorkflow


class TaskManager:
    """Manager for task operations with repository pattern.

    Provides a high-level API for task management including:
    - Creating tasks (via TaskQAWorkflow)
    - Querying tasks (via TaskRepository)

    Uses TaskQAWorkflow for operations that coordinate Task + QA.
    Uses TaskRepository for persistence-only operations.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize task manager.

        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
        self._repo = TaskRepository(project_root=self.project_root)
        self._workflow = TaskQAWorkflow(project_root=self.project_root)

    def create_task(
        self,
        task_id: str,
        title: str,
        *,
        description: str = "",
        session_id: Optional[str] = None,
        owner: Optional[str] = None,
        create_qa: bool = True,
    ) -> Task:
        """Create a new task.

        Args:
            task_id: Task identifier
            title: Task title
            description: Task description
            session_id: Associated session
            owner: Task owner
            create_qa: Whether to create associated QA record (default: True)

        Returns:
            Created task
        """
        # Delegate to workflow for operations coordinating Task + QA
        return self._workflow.create_task(
            task_id=task_id,
            title=title,
            description=description,
            session_id=session_id,
            owner=owner,
            create_qa=create_qa,
        )

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task if found, None otherwise
        """
        return self._repo.get(task_id)

    def list_tasks(self, state: Optional[str] = None) -> List[Task]:
        """List tasks, optionally filtered by state.
        
        Args:
            state: State to filter by (optional)
            
        Returns:
            List of tasks
        """
        if state:
            return self._repo.list_by_state(state)
        return self._repo.get_all()

    def find_tasks_by_session(self, session_id: str) -> List[Task]:
        """Find tasks belonging to a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of tasks in the session
        """
        return self._repo.find_by_session(session_id)



__all__ = ["TaskManager"]
