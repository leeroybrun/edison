"""Test helper functions for task operations.

This module provides convenience functions for tests using the
TaskRepository and Task entity APIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from tests.helpers.fixtures import create_task_file


def ensure_task(
    task_id: str,
    state: str = "todo",
    session_id: Optional[str] = None,
    project_root: Optional[Path] = None,
    title: Optional[str] = None,
) -> Any:
    """Ensure a task exists, creating it if necessary.

    This is a convenience wrapper around create_task_file that provides
    similar semantics to ensure_session.

    Args:
        task_id: Task identifier
        state: Task state (default: "todo")
        session_id: Optional session ID for the task
        project_root: Project root path (uses auto-detection if None)
        title: Optional task title

    Returns:
        The Task object (created or existing)
    """
    from edison.core.task.repository import TaskRepository

    # Determine project root
    if project_root is None:
        from edison.core.utils.paths import find_repo_root
        project_root = find_repo_root()

    repo = TaskRepository(project_root=project_root)

    # Check if task already exists
    existing = repo.get(task_id)
    if existing is not None:
        return existing

    # Create the task
    return create_task_file(
        repo_path=project_root,
        task_id=task_id,
        state=state,
        session_id=session_id,
        title=title,
    )


__all__ = ["ensure_task"]
