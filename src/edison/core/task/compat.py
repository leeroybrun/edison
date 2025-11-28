"""Compatibility layer for legacy task record API.

This module provides backward-compatible functions that bridge the old
JSON-based task record API to the new Repository-based implementation.

These functions are provided for test compatibility and will be deprecated
once all tests are migrated to use the Repository pattern directly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from edison.core.utils.paths import PathResolver
from edison.core.utils.time import utc_timestamp
from edison.core.config.domains import TaskConfig

from .models import Task
from .repository import TaskRepository


# Global repository instance (lazy-loaded)
_repo: Optional[TaskRepository] = None


def _get_repo() -> TaskRepository:
    """Get or create the global repository instance."""
    global _repo
    if _repo is None:
        _repo = TaskRepository()
    return _repo


def _get_meta_dir() -> Path:
    """Get the task metadata directory for JSON storage."""
    project_root = PathResolver.resolve_project_root()
    config = TaskConfig(repo_root=project_root)
    meta_dir = config.tasks_root() / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir


def _get_meta_path(task_id: str) -> Path:
    """Get path to task metadata JSON file."""
    return _get_meta_dir() / f"{task_id}.json"


def _read_meta(task_id: str) -> Dict[str, Any]:
    """Read task metadata from JSON file."""
    path = _get_meta_path(task_id)
    if not path.exists():
        raise FileNotFoundError(f"Task record not found: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_meta(task_id: str, data: Dict[str, Any]) -> None:
    """Write task metadata to JSON file."""
    path = _get_meta_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_task_record(
    task_id_or_title: Optional[str] = None,
    title: Optional[str] = None,
    *,
    description: str = "",
    status: str = "todo",
    session_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
) -> str:
    """Create a task record with optional session linkage.

    Supports three call signatures:
    1. create_task_record(title="...", session_id=...) - auto-generates task_id
    2. create_task_record(title, session_id=...) - auto-generates task_id
    3. create_task_record(task_id, title) - uses provided task_id

    Args:
        task_id_or_title: Either task_id (if title is provided) or title (if title is None)
        title: Task title (if first arg is task_id, or if using keyword args)
        description: Task description
        status: Task status (default: "todo")
        session_id: Optional session ID to link this task to
        parent_task_id: Optional parent task ID for delegation

    Returns:
        str: The task_id that was created
    """
    # Determine call signature
    if task_id_or_title is None and title is not None:
        # Called as create_task_record(title="...", ...)
        task_id = f"task-{uuid4().hex[:8]}"
    elif task_id_or_title is not None and title is None:
        # Called as create_task_record(title, ...) - positional title
        title = task_id_or_title
        task_id = f"task-{uuid4().hex[:8]}"
    elif task_id_or_title is not None and title is not None:
        # Called as create_task_record(task_id, title)
        task_id = task_id_or_title
    else:
        raise ValueError("Must provide either task_id_or_title or title")

    # Create task via repository (for markdown file)
    repo = _get_repo()

    # Check if task already exists in repository
    existing_task = repo.get(task_id)
    if existing_task is not None:
        # Task already exists - just update metadata and return
        _write_meta(task_id, {
            "id": task_id,
            "title": title,
            "description": description,
            "status": status,
            "created_at": utc_timestamp(),
            "updated_at": utc_timestamp(),
            "child_tasks": [],
            "session_id": session_id,
            "parent_task_id": parent_task_id,
        })
        return task_id

    task = Task.create(
        task_id=task_id,
        title=title,
        description=description,
        session_id=session_id,
        state=status,
    )

    if parent_task_id:
        task.parent_id = parent_task_id

    repo.create(task)

    # Create metadata JSON for compatibility
    meta = {
        "id": task_id,
        "title": title,
        "description": description,
        "status": status,
        "created_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
        "child_tasks": [],
    }

    if session_id:
        meta["session_id"] = session_id
        # Register task with session
        try:
            from edison.core.session.graph import register_task
            from edison.core.task import default_owner
            register_task(
                session_id=session_id,
                task_id=task_id,
                owner=default_owner(),
                status=status,
            )
        except Exception:
            pass  # Session registration is optional for compatibility

    if parent_task_id:
        meta["parent_task_id"] = parent_task_id
        # Update parent's child_tasks list
        try:
            parent_meta = _read_meta(parent_task_id)
            child_tasks = parent_meta.get("child_tasks", [])
            if task_id not in child_tasks:
                child_tasks.append(task_id)
                parent_meta["child_tasks"] = child_tasks
                parent_meta["updated_at"] = utc_timestamp()
                _write_meta(parent_task_id, parent_meta)
        except FileNotFoundError:
            pass  # Parent doesn't exist yet

    _write_meta(task_id, meta)

    return task_id


def load_task_record(task_id: str) -> Dict[str, Any]:
    """Load a task record.

    Args:
        task_id: Task identifier

    Returns:
        Dict[str, Any]: Task record data

    Raises:
        FileNotFoundError: If task record not found
    """
    return _read_meta(task_id)


def update_task_record(
    task_id: str,
    updates: Dict[str, Any],
    *,
    operation: str = "update",
) -> Dict[str, Any]:
    """Update a task record.

    Args:
        task_id: Task identifier
        updates: Dict of fields to update
        operation: Operation type (for logging)

    Returns:
        Dict[str, Any]: Updated task record
    """
    # Load existing metadata
    try:
        record = _read_meta(task_id)
    except FileNotFoundError:
        # Create new record if it doesn't exist
        record = {
            "id": task_id,
            "title": updates.get("title", ""),
            "status": updates.get("status", "todo"),
            "created_at": utc_timestamp(),
            "child_tasks": [],
        }

    # Apply updates
    record.update(updates)
    record["updated_at"] = utc_timestamp()
    record["operation"] = operation

    # Write back
    _write_meta(task_id, record)

    # Update repository if needed
    try:
        repo = _get_repo()
        task = repo.get(task_id)
        if task:
            # Update task entity fields
            if "status" in updates:
                task.state = updates["status"]
            if "title" in updates:
                task.title = updates["title"]
            if "description" in updates:
                task.description = updates["description"]
            if "result" in updates:
                task.result = str(updates["result"])

            repo.save(task)
    except Exception:
        pass  # Repository update is optional for compatibility

    return record


def set_task_result(
    task_id: str,
    *,
    status: Optional[str] = None,
    result: Any = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Set the result/status of a task.

    Args:
        task_id: Task identifier
        status: Optional status to set (e.g., 'success', 'failure')
        result: Optional result data (can be dict or any value)
        error: Optional error message

    Returns:
        Dict[str, Any]: Updated task record
    """
    updates: Dict[str, Any] = {}

    if status:
        updates["status"] = status
    if result is not None:
        updates["result"] = result
    if error is not None:
        updates["error"] = error

    return update_task_record(task_id, updates, operation="set_result")


__all__ = [
    "create_task_record",
    "load_task_record",
    "update_task_record",
    "set_task_result",
]
