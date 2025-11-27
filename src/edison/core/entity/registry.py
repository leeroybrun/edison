"""Base registry for read-only, composed content.

This module provides the abstract base class for content registries that
discover and compose content from layered sources (core → packs → project).

Registries are read-only - they discover and compose content but don't
create, update, or delete it. This is in contrast to repositories which
provide full CRUD operations for mutable entities.

Architecture:
    BaseEntityManager
    └── BaseRegistry (this module)
        ├── AgentRegistry
        ├── ValidatorRegistry
        ├── GuidelineRegistry
        ├── RulesRegistry
        └── FilePatternRegistry
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar

from .manager import BaseEntityManager
from .base import EntityId

# Type variable for registry content types
T = TypeVar("T")


class BaseRegistry(BaseEntityManager[T], Generic[T]):
    """Abstract base class for content registries.
    
    Provides a framework for discovering and composing content from
    Edison's layered structure: core → packs → project.
    
    Subclasses implement the discovery methods for their specific
    content type and can customize composition behavior.
    
    Features:
    - Layered discovery (core, packs, project)
    - Optional caching for performance
    - Consistent interface with repositories (exists, get, get_all)
    
    Type Parameters:
        T: The content type this registry manages (e.g., Agent, Validator)
    
    Attributes:
        entity_type: String identifier for the content type
        project_root: Root path of the project
        project_dir: Project configuration directory
        core_dir: Directory for core/bundled content
        packs_dir: Directory for pack content
    """
    
    # Cache for discovered content - subclasses can enable caching
    _cache: Optional[Dict[str, T]] = None
    _cache_enabled: bool = False
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize registry with path resolution.
        
        Args:
            project_root: Project root directory. If not provided,
                uses PathResolver to detect automatically.
        """
        super().__init__(project_root)
        
        # Standard directory layout for composition
        self.core_dir = self.project_dir / "core"
        self.packs_dir = self.project_dir / "packs"
    
    # ---------- Caching ----------
    
    def invalidate_cache(self) -> None:
        """Clear the discovery cache.
        
        Call this when underlying content may have changed.
        """
        self._cache = None
    
    def _get_cached(self, entity_id: EntityId) -> Optional[T]:
        """Get entity from cache if available.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Cached entity or None if not cached
        """
        if self._cache is None:
            return None
        return self._cache.get(entity_id)
    
    def _set_cached(self, entity_id: EntityId, entity: T) -> None:
        """Store entity in cache.
        
        Args:
            entity_id: Entity identifier
            entity: Entity to cache
        """
        if self._cache_enabled:
            if self._cache is None:
                self._cache = {}
            self._cache[entity_id] = entity
    
    # ---------- Discovery Interface ----------
    
    @abstractmethod
    def discover_core(self) -> Dict[str, T]:
        """Discover content from core/bundled sources.
        
        Returns:
            Dict mapping entity names to entities from core layer
        """
        pass
    
    @abstractmethod
    def discover_packs(self, packs: List[str]) -> Dict[str, T]:
        """Discover content from active packs.
        
        Args:
            packs: List of active pack names
            
        Returns:
            Dict mapping entity names to entities from pack layers
        """
        pass
    
    @abstractmethod
    def discover_project(self) -> Dict[str, T]:
        """Discover content from project layer.
        
        Returns:
            Dict mapping entity names to entities from project layer
        """
        pass
    
    def discover_all(self, packs: Optional[List[str]] = None) -> Dict[str, T]:
        """Discover all content across all layers.
        
        Merges content from core, packs, and project layers.
        Later layers override earlier ones.
        
        Args:
            packs: Optional list of active pack names
            
        Returns:
            Dict mapping entity names to entities
        """
        result: Dict[str, T] = {}
        
        # Core layer (lowest priority)
        result.update(self.discover_core())
        
        # Pack layers (in order)
        if packs:
            result.update(self.discover_packs(packs))
        
        # Project layer (highest priority)
        result.update(self.discover_project())
        
        return result
    
    # ---------- Composition Interface ----------
    
    def compose(
        self,
        name: str,
        packs: Optional[List[str]] = None,
    ) -> Optional[T]:
        """Compose a single entity from all layers.
        
        This is the primary composition method. Subclasses may override
        to implement specific composition strategies (section-based,
        concatenate, YAML merge, etc.).
        
        Args:
            name: Entity name to compose
            packs: Optional list of active pack names
            
        Returns:
            Composed entity or None if not found
        """
        # Default implementation: just discover and return
        all_entities = self.discover_all(packs)
        return all_entities.get(name)
    
    # ---------- BaseEntityManager Interface ----------
    
    def exists(self, entity_id: EntityId) -> bool:
        """Check if an entity exists in any layer.
        
        Args:
            entity_id: Entity identifier (name)
            
        Returns:
            True if entity exists in core, packs, or project
        """
        # Check cache first
        if self._cache is not None and entity_id in self._cache:
            return True
        
        # Check core
        if entity_id in self.discover_core():
            return True
        
        # For a full check, we'd need to check packs and project too
        # But that requires knowing active packs
        return False
    
    def get(self, entity_id: EntityId) -> Optional[T]:
        """Get an entity by ID.
        
        Note: For full composition, use compose() with pack list.
        This method only checks core layer by default.
        
        Args:
            entity_id: Entity identifier (name)
            
        Returns:
            Entity if found in core layer, None otherwise
        """
        # Check cache first
        cached = self._get_cached(entity_id)
        if cached is not None:
            return cached
        
        # Discover from core
        core = self.discover_core()
        return core.get(entity_id)
    
    def get_all(self) -> List[T]:
        """Get all entities from core layer.
        
        Note: For all entities including packs, use discover_all() with pack list.
        
        Returns:
            List of all entities from core layer
        """
        return list(self.discover_core().values())
    
    # ---------- Utility Methods ----------
    
    def list_names(self, packs: Optional[List[str]] = None) -> List[str]:
        """List all entity names across layers.
        
        Args:
            packs: Optional list of active pack names
            
        Returns:
            Sorted list of entity names
        """
        all_entities = self.discover_all(packs)
        return sorted(all_entities.keys())


__all__ = [
    "BaseRegistry",
]
