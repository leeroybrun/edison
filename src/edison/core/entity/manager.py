"""Base entity manager - foundation for all entity/content management.

This module provides the abstract base class that both repositories (mutable)
and registries (read-only) extend. It defines the common interface and
initialization pattern for managing entities in Edison.

Architecture:
    BaseEntityManager (this module)
    ├── BaseRepository - CRUD operations + state transitions (mutable)
    └── BaseRegistry - Layered discovery + composition (read-only)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_project_config_dir

from .base import EntityId
from .exceptions import EntityNotFoundError

# Type variable for entity types
T = TypeVar("T")


class BaseEntityManager(Generic[T], ABC):
    """Abstract base class for all entity/content managers.
    
    Provides common initialization, path resolution, and a consistent
    interface for checking existence and retrieving entities.
    
    Extended by:
    - BaseRepository: For mutable, stateful entities (tasks, sessions)
    - BaseRegistry: For read-only, composed content (agents, validators)
    
    Type Parameters:
        T: The entity type this manager handles
    
    Attributes:
        entity_type: String identifier for the entity type (e.g., "task", "agent")
        project_root: Root path of the project
        project_dir: Project configuration directory (<project-config-dir> or similar)
    """
    
    # Entity type identifier - subclasses should override
    entity_type: str = "entity"
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize entity manager with path resolution.
        
        Args:
            project_root: Project root directory. If not provided,
                uses PathResolver to detect automatically.
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)
    
    # ---------- Core Interface ----------
    
    @abstractmethod
    def exists(self, entity_id: EntityId) -> bool:
        """Check if an entity exists.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            True if entity exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get(self, entity_id: EntityId) -> Optional[T]:
        """Get an entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    def get_or_raise(self, entity_id: EntityId) -> T:
        """Get an entity by ID, raising if not found.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity
            
        Raises:
            EntityNotFoundError: If entity not found
        """
        entity = self.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(
                f"{self.entity_type.title()} '{entity_id}' not found",
                entity_type=self.entity_type,
                entity_id=entity_id,
            )
        return entity
    
    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities managed by this manager
        """
        pass


__all__ = [
    "BaseEntityManager",
]
