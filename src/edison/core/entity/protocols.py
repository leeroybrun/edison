"""Protocols for entity types.

This module defines the protocols (interfaces) that entities must implement
to work with the repository pattern, registry pattern, and state management.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Protocol, TypeVar, runtime_checkable


@runtime_checkable
class Identifiable(Protocol):
    """Protocol for entities with an ID."""
    
    @property
    def id(self) -> str:
        """Unique entity identifier."""
        ...


@runtime_checkable  
class StatefulEntity(Protocol):
    """Protocol for entities with state that can be transitioned.
    
    Entities implementing this protocol can be used with the unified
    state transition system.
    """
    
    @property
    def id(self) -> str:
        """Unique entity identifier."""
        ...
    
    @property
    def state(self) -> str:
        """Current entity state."""
        ...
    
    @state.setter
    def state(self, value: str) -> None:
        """Set entity state."""
        ...


@runtime_checkable
class Persistable(Protocol):
    """Protocol for entities that can be serialized/deserialized.
    
    Entities implementing this protocol can be persisted to storage
    (files, databases, etc.) and restored.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize entity to dictionary.
        
        Returns:
            Dict representation of the entity
        """
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persistable":
        """Deserialize entity from dictionary.
        
        Args:
            data: Dict representation of the entity
            
        Returns:
            Reconstructed entity instance
        """
        ...


@runtime_checkable
class Entity(Identifiable, StatefulEntity, Persistable, Protocol):
    """Combined protocol for full entity support.
    
    Entities implementing this protocol have:
    - Unique ID
    - Mutable state
    - Serialization support
    """
    pass


@runtime_checkable
class Discoverable(Protocol):
    """Protocol for content that can be discovered from layers.
    
    Content implementing this protocol can be managed by registries
    and discovered from core, pack, and project layers.
    
    This is used for read-only content like agents, validators,
    guidelines, and rules.
    """
    
    @property
    def name(self) -> str:
        """Content name/identifier."""
        ...
    
    @property
    def source_path(self) -> Optional[Path]:
        """Path to source file, if applicable."""
        ...


# Type variable for generic entity operations
T = TypeVar("T", bound=Identifiable)
EntityT = TypeVar("EntityT", bound=Entity)
DiscoverableT = TypeVar("DiscoverableT", bound=Discoverable)


__all__ = [
    "Identifiable",
    "StatefulEntity",
    "Persistable",
    "Entity",
    "Discoverable",
    "T",
    "EntityT",
    "DiscoverableT",
]


