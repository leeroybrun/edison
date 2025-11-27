"""Base repository pattern for entities.

This module provides the abstract base class for entity repositories.
Repositories handle CRUD operations and state transitions for entities.

The repository pattern separates data access from business logic,
making code more testable and maintainable.

Architecture:
    BaseEntityManager
    └── BaseRepository (this module)
        └── Concrete repositories (TaskRepository, SessionRepository, etc.)

Example usage:
    class TaskRepository(BaseRepository[Task]):
        def _do_create(self, entity: Task) -> Task:
            # Implementation
            ...
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional, TypeVar

from .base import EntityId
from .manager import BaseEntityManager
from .protocols import Entity
from .exceptions import (
    EntityExistsError,
    EntityStateError,
)

# Type variable for entity types
T = TypeVar("T", bound=Entity)


class BaseRepository(BaseEntityManager[T]):
    """Abstract base repository for entity CRUD operations.
    
    Extends BaseEntityManager with CRUD operations (create, save, delete)
    and state transition support for mutable, stateful entities.
    
    Subclasses must implement the abstract _do_* methods for their specific
    storage backend.
    
    Type Parameters:
        T: The entity type this repository manages
    """
    
    # ---------- CRUD Operations ----------
    
    def create(self, entity: T) -> T:
        """Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity (may have updated fields)
            
        Raises:
            EntityExistsError: If entity already exists
            PersistenceError: If creation fails
        """
        if self.exists(entity.id):
            raise EntityExistsError(
                f"{self.entity_type.title()} {entity.id} already exists",
                entity_type=self.entity_type,
                entity_id=entity.id,
            )
        return self._do_create(entity)
    
    @abstractmethod
    def _do_create(self, entity: T) -> T:
        """Implementation of create operation.
        
        Subclasses must implement this method.
        """
        pass
    
    def exists(self, entity_id: EntityId) -> bool:
        """Check if an entity exists.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            True if entity exists
        """
        return self._do_exists(entity_id)
    
    @abstractmethod
    def _do_exists(self, entity_id: EntityId) -> bool:
        """Implementation of exists check.
        
        Subclasses must implement this method.
        """
        pass
    
    def get(self, entity_id: EntityId) -> Optional[T]:
        """Get an entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity if found, None otherwise
        """
        return self._do_get(entity_id)
    
    @abstractmethod
    def _do_get(self, entity_id: EntityId) -> Optional[T]:
        """Implementation of get operation.
        
        Subclasses must implement this method.
        """
        pass
    
    def get_all(self) -> List[T]:
        """Get all entities.
        
        Returns:
            List of all entities
        """
        return self._do_list_all()
    
    def save(self, entity: T) -> None:
        """Save an entity (update existing or create new).
        
        Args:
            entity: Entity to save
            
        Raises:
            PersistenceError: If save fails
        """
        self._do_save(entity)
    
    @abstractmethod
    def _do_save(self, entity: T) -> None:
        """Implementation of save operation.
        
        Subclasses must implement this method.
        """
        pass
    
    def delete(self, entity_id: EntityId) -> bool:
        """Delete an entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            True if entity was deleted, False if not found
        """
        return self._do_delete(entity_id)
    
    @abstractmethod
    def _do_delete(self, entity_id: EntityId) -> bool:
        """Implementation of delete operation.
        
        Subclasses must implement this method.
        """
        pass
    
    # ---------- Query Operations ----------
    
    def find(self, **criteria: Any) -> List[T]:
        """Find entities matching criteria.
        
        Args:
            **criteria: Key-value pairs to match
            
        Returns:
            List of matching entities
        """
        return self._do_find(**criteria)
    
    @abstractmethod
    def _do_find(self, **criteria: Any) -> List[T]:
        """Implementation of find operation.
        
        Subclasses must implement this method.
        """
        pass
    
    def list_by_state(self, state: str) -> List[T]:
        """List entities in a given state.
        
        Args:
            state: State to filter by
            
        Returns:
            List of entities in the state
        """
        return self._do_list_by_state(state)
    
    @abstractmethod
    def _do_list_by_state(self, state: str) -> List[T]:
        """Implementation of list_by_state operation.
        
        Subclasses must implement this method.
        """
        pass
    
    def list_all(self) -> List[T]:
        """List all entities.
        
        Alias for get_all() for backward compatibility.
        
        Returns:
            List of all entities
        """
        return self._do_list_all()
    
    @abstractmethod
    def _do_list_all(self) -> List[T]:
        """Implementation of list_all operation.
        
        Subclasses must implement this method.
        """
        pass
    
    # ---------- State Transition ----------
    
    def transition(
        self, 
        entity_id: EntityId, 
        to_state: str,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> T:
        """Transition an entity to a new state.
        
        This method:
        1. Gets the entity
        2. Validates the transition
        3. Updates the state
        4. Records history
        5. Persists changes
        
        Args:
            entity_id: Entity identifier
            to_state: Target state
            context: Optional context for transition
            
        Returns:
            Updated entity
            
        Raises:
            EntityNotFoundError: If entity not found
            EntityStateError: If transition not allowed
        """
        from edison.core.state.transitions import validate_transition
        
        entity = self.get_or_raise(entity_id)
        from_state = entity.state
        
        # Validate transition
        valid, error = validate_transition(
            self.entity_type,
            from_state,
            to_state,
            context=context,
        )
        if not valid:
            raise EntityStateError(
                error or f"Cannot transition from {from_state} to {to_state}",
                entity_type=self.entity_type,
                entity_id=entity_id,
                from_state=from_state,
                to_state=to_state,
            )
        
        # Update state
        entity.state = to_state
        
        # Record history if entity supports it
        if hasattr(entity, "record_transition"):
            entity.record_transition(from_state, to_state)
        elif hasattr(entity, "state_history"):
            from .base import StateHistoryEntry
            entry = StateHistoryEntry.create(from_state, to_state)
            entity.state_history.append(entry)
        
        # Persist
        self.save(entity)
        
        return entity


__all__ = [
    "BaseRepository",
]
