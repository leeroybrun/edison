"""Base registry for read-only entity lookup.

Extends BaseEntityManager with read-only semantics.
Unlike BaseRepository (CRUD), registries only provide read operations.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import List, TypeVar

from edison.core.entity.manager import BaseEntityManager

T = TypeVar("T")


class BaseRegistry(BaseEntityManager[T]):
    """Read-only entity registry.
    
    Provides read-only access to entities without CRUD operations.
    
    Subclasses must implement:
    - exists(entity_id) - Check if entity exists
    - get(entity_id) - Get entity by ID
    - get_all() - Get all entities
    - list_names() - List all entity names
    
    Unlike BaseRepository, BaseRegistry does not support:
    - create()
    - save()
    - delete()
    - transition()
    """
    
    @abstractmethod
    def list_names(self) -> List[str]:
        """List all entity names/IDs.
        
        Returns:
            Sorted list of entity identifiers
        """
        pass


__all__ = ["BaseRegistry"]
