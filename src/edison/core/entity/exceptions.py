"""Entity-related exceptions.

This module defines exceptions for entity operations including
repository errors, validation errors, and state transition errors.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class EntityError(Exception):
    """Base exception for entity operations."""
    
    def __init__(
        self,
        message: str,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.context = context or {}


class EntityNotFoundError(EntityError):
    """Raised when an entity is not found."""
    
    def __init__(
        self,
        message: str = "Entity not found",
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            entity_type=entity_type,
            entity_id=entity_id,
        )


class EntityValidationError(EntityError):
    """Raised when entity validation fails."""
    
    def __init__(
        self,
        message: str,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        field: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            entity_type=entity_type,
            entity_id=entity_id,
            context={"field": field} if field else {},
        )
        self.field = field


class EntityExistsError(EntityError):
    """Raised when trying to create an entity that already exists."""
    
    def __init__(
        self,
        message: str = "Entity already exists",
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> None:
        super().__init__(
            message,
            entity_type=entity_type,
            entity_id=entity_id,
        )


class EntityStateError(EntityError):
    """Raised when an entity state operation fails."""
    
    def __init__(
        self,
        message: str,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
    ) -> None:
        context = {}
        if from_state:
            context["from_state"] = from_state
        if to_state:
            context["to_state"] = to_state
        super().__init__(
            message,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
        )
        self.from_state = from_state
        self.to_state = to_state


class RepositoryError(EntityError):
    """Base exception for repository operations."""
    pass


class PersistenceError(RepositoryError):
    """Raised when entity persistence fails."""
    pass


class LockError(RepositoryError):
    """Raised when unable to acquire a lock on an entity."""
    pass


__all__ = [
    "EntityError",
    "EntityNotFoundError",
    "EntityValidationError",
    "EntityExistsError",
    "EntityStateError",
    "RepositoryError",
    "PersistenceError",
    "LockError",
]


