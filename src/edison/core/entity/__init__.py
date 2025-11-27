"""Entity framework for Edison.

This module provides the foundation for entity management:

- **Protocols**: Type definitions for entities (StatefulEntity, Persistable)
- **Base classes**: EntityMetadata, BaseEntity, StateHistoryEntry
- **Repository pattern**: BaseRepository for CRUD operations
- **File persistence**: FileRepositoryMixin for file-based storage

Example usage:
    from edison.core.entity import BaseRepository, BaseEntity, EntityMetadata
    
    @dataclass
    class Task(BaseEntity):
        title: str
        description: str
    
    class TaskRepository(BaseRepository[Task]):
        entity_type = "task"
        # Implement abstract methods...
"""
from __future__ import annotations

from .protocols import (
    Identifiable,
    StatefulEntity,
    Persistable,
    Entity,
    Discoverable,
    T,
    EntityT,
    DiscoverableT,
)
from .base import (
    EntityId,
    EntityMetadata,
    StateHistoryEntry,
    BaseEntity,
)
from .exceptions import (
    EntityError,
    EntityNotFoundError,
    EntityValidationError,
    EntityExistsError,
    EntityStateError,
    RepositoryError,
    PersistenceError,
    LockError,
)
from .manager import BaseEntityManager
from .registry import BaseRegistry
from .repository import BaseRepository
from .file_repository import (
    FileRepositoryMixin,
    FileLockMixin,
)

__all__ = [
    # Protocols
    "Identifiable",
    "StatefulEntity",
    "Persistable",
    "Entity",
    "Discoverable",
    "T",
    "EntityT",
    "DiscoverableT",
    # Base types
    "EntityId",
    "EntityMetadata",
    "StateHistoryEntry",
    "BaseEntity",
    # Exceptions
    "EntityError",
    "EntityNotFoundError",
    "EntityValidationError",
    "EntityExistsError",
    "EntityStateError",
    "RepositoryError",
    "PersistenceError",
    "LockError",
    # Manager base
    "BaseEntityManager",
    # Registry base
    "BaseRegistry",
    # Repository
    "BaseRepository",
    "FileRepositoryMixin",
    "FileLockMixin",
]


