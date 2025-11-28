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

    def _do_find(self, **criteria: Any) -> List[T]:
        """Default find implementation using attribute matching.

        Filters entities by matching all criteria against entity attributes.
        Subclasses can override for optimized queries.

        Args:
            **criteria: Key-value pairs to match against entity attributes

        Returns:
            List of entities where all criteria match
        """
        if not criteria:
            return self._do_list_all()

        return [
            entity for entity in self._do_list_all()
            if all(getattr(entity, k, None) == v for k, v in criteria.items())
        ]
    
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
        2. Validates the transition (via transition_entity)
        3. Executes configured actions (via transition_entity)
        4. Updates the state
        5. Records history
        6. Persists changes

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
        from edison.core.state.transitions import transition_entity, EntityTransitionError

        entity = self.get_or_raise(entity_id)
        from_state = entity.state

        # Use unified transition system with full validation and action execution
        try:
            result = transition_entity(
                entity_type=self.entity_type,
                entity_id=str(entity_id),
                to_state=to_state,
                current_state=from_state,
                context=context,
                record_history=True,
            )
        except EntityTransitionError as e:
            raise EntityStateError(
                str(e),
                entity_type=self.entity_type,
                entity_id=entity_id,
                from_state=from_state,
                to_state=to_state,
            ) from e

        # Update entity state from transition result
        entity.state = result["state"]

        # Record history if entity supports it and we have a history entry
        if "history_entry" in result:
            if hasattr(entity, "record_transition"):
                entity.record_transition(
                    from_state=result["history_entry"]["from"],
                    to_state=result["history_entry"]["to"],
                )
            elif hasattr(entity, "state_history"):
                from .base import StateHistoryEntry
                entry = StateHistoryEntry.create(
                    from_state=result["history_entry"]["from"],
                    to_state=result["history_entry"]["to"],
                )
                entity.state_history.append(entry)

        # Persist
        self.save(entity)

        return entity


__all__ = [
    "BaseRepository",
]
