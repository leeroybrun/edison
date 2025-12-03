"""Example Python module following Edison Python pack standards.

This module demonstrates:
- Modern Python 3.12+ patterns
- Strict type annotations
- Dataclasses for data structures
- Protocol for duck typing
- Proper error handling
- Configuration from YAML (no hardcoding)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Protocol, TypeVar

import yaml


# =============================================================================
# Enums for Constants
# =============================================================================


class TaskStatus(Enum):
    """Task lifecycle states."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


# =============================================================================
# Data Models (Dataclasses)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Task:
    """Immutable task entity.

    Attributes:
        id: Unique task identifier
        title: Task title
        status: Current task status
        created_at: Creation timestamp
    """

    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    def with_status(self, status: TaskStatus) -> Task:
        """Return new task with updated status (immutable update)."""
        return Task(
            id=self.id,
            title=self.title,
            status=status,
            created_at=self.created_at,
        )


# =============================================================================
# Protocols (Duck Typing)
# =============================================================================

T = TypeVar("T")


class Repository(Protocol[T]):
    """Repository interface for any entity type."""

    def get(self, id: str) -> T | None:
        """Get entity by ID."""
        ...

    def save(self, entity: T) -> None:
        """Save entity."""
        ...

    def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        ...


# =============================================================================
# Custom Exceptions
# =============================================================================


class DomainError(Exception):
    """Base exception for domain errors."""

    pass


class NotFoundError(DomainError):
    """Raised when entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")


class ValidationError(DomainError):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


# =============================================================================
# Configuration Loading (No Hardcoding)
# =============================================================================


def load_config(config_path: Path) -> dict[str, object]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if config is None:
        return {}

    return config


# =============================================================================
# Repository Implementation
# =============================================================================


class FileTaskRepository:
    """File-based task repository.

    Stores tasks as JSON files in a directory.
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialize repository.

        Args:
            base_dir: Directory for storing task files
        """
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, id: str) -> Path:
        """Get path for task file."""
        return self._base_dir / f"{id}.json"

    def get(self, id: str) -> Task | None:
        """Get task by ID.

        Args:
            id: Task identifier

        Returns:
            Task if found, None otherwise
        """
        path = self._task_path(id)
        if not path.exists():
            return None

        import json

        data = json.loads(path.read_text())
        return Task(
            id=data["id"],
            title=data["title"],
            status=TaskStatus[data["status"]],
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def save(self, task: Task) -> None:
        """Save task.

        Args:
            task: Task to save
        """
        import json

        data = {
            "id": task.id,
            "title": task.title,
            "status": task.status.name,
            "created_at": task.created_at.isoformat(),
        }
        self._task_path(task.id).write_text(json.dumps(data, indent=2))

    def delete(self, id: str) -> bool:
        """Delete task by ID.

        Args:
            id: Task identifier

        Returns:
            True if deleted, False if not found
        """
        path = self._task_path(id)
        if not path.exists():
            return False

        path.unlink()
        return True


# =============================================================================
# Service Layer
# =============================================================================


class TaskService:
    """Task business logic service."""

    def __init__(self, repository: Repository[Task]) -> None:
        """Initialize service with repository.

        Args:
            repository: Task repository implementation
        """
        self._repository = repository

    def create_task(self, title: str) -> Task:
        """Create a new task.

        Args:
            title: Task title

        Returns:
            Created task

        Raises:
            ValidationError: If title is empty
        """
        if not title or not title.strip():
            raise ValidationError("title", "cannot be empty")

        import uuid

        task = Task(
            id=str(uuid.uuid4()),
            title=title.strip(),
        )
        self._repository.save(task)
        return task

    def get_task(self, id: str) -> Task:
        """Get task by ID.

        Args:
            id: Task identifier

        Returns:
            Task

        Raises:
            NotFoundError: If task not found
        """
        task = self._repository.get(id)
        if task is None:
            raise NotFoundError("Task", id)
        return task

    def complete_task(self, id: str) -> Task:
        """Mark task as completed.

        Args:
            id: Task identifier

        Returns:
            Updated task

        Raises:
            NotFoundError: If task not found
        """
        task = self.get_task(id)
        updated = task.with_status(TaskStatus.COMPLETED)
        self._repository.save(updated)
        return updated
