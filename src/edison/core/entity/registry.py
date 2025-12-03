"""Base registry for read-only, composed content.

This module provides the abstract base class for content registries that
discover and compose content from layered sources (core → packs → project).

Registries are read-only - they discover and compose content but don't
create, update, or delete it. This is in contrast to repositories which
provide full CRUD operations for mutable entities.

Architecture:
    CompositionBase (provides path resolution, config, YAML utilities)
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
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar

from .base import EntityId
from edison.core.composition.core.paths import CompositionPathResolver

# Use TYPE_CHECKING to avoid circular import at runtime
if TYPE_CHECKING:
    from edison.core.composition.core.base import CompositionBase as CompositionBaseType

# Type variable for registry content types
T = TypeVar("T")


def _get_composition_base() -> type:
    """Lazy import CompositionBase to avoid circular import."""
    from edison.core.composition.core.base import CompositionBase
    return CompositionBase


class BaseRegistry(Generic[T]):
    """Abstract base class for content registries.

    Uses CompositionBase (via lazy import) for unified path resolution,
    config management, and YAML utilities. Provides a framework for discovering
    and composing content from Edison's layered structure: core → packs → project.

    Subclasses implement the discovery methods for their specific
    content type and can customize composition behavior.

    Features:
    - Unified path/config via CompositionBase
    - Layered discovery (core, packs, project)
    - Optional caching for performance
    - Consistent interface (exists, get, get_all)

    Type Parameters:
        T: The content type this registry manages (e.g., Agent, Validator)

    Attributes:
        entity_type: String identifier for the content type
        project_root: Root path of the project
        project_dir: Project configuration directory
        core_dir: Directory for core/bundled content
        bundled_packs_dir: Directory for bundled pack content
        project_packs_dir: Directory for project pack content
    """

    # Entity type identifier - subclasses should override
    entity_type: str = "entity"

    # Cache for discovered content - subclasses can enable caching
    _cache: Optional[Dict[str, T]] = None
    _cache_enabled: bool = False

    # Declare attributes for type checking (set by _init_composition)
    project_root: Path
    project_dir: Path
    core_dir: Path
    bundled_packs_dir: Path
    project_packs_dir: Path
    cfg_mgr: Any
    config: Dict[str, Any]
    _packs_config_cache: Any

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize registry with path resolution via CompositionBase.

        Args:
            project_root: Project root directory. If not provided,
                uses PathResolver to detect automatically.
        """
        # Initialize composition infrastructure (central resolver, no legacy)
        resolver = CompositionPathResolver(project_root)
        self.project_root = resolver.repo_root
        self.project_dir = resolver.project_dir
        self.core_dir = resolver.core_dir
        self.bundled_packs_dir = resolver.bundled_packs_dir
        self.project_packs_dir = resolver.project_packs_dir

        from edison.core.config import ConfigManager
        self.cfg_mgr = ConfigManager(self.project_root)
        self.config = self.cfg_mgr.load_config(validate=False)
        self._packs_config_cache = None

    def _init_composition(self, project_root: Optional[Path] = None) -> None:
        # Deprecated placeholder for legacy callers; now handled in __init__
        return

    # =========================================================================
    # Active Packs (from CompositionBase pattern)
    # =========================================================================

    def get_active_packs(self) -> List[str]:
        """Get active packs list (cached)."""
        if self._packs_config_cache is None:
            from edison.core.config.domains import PacksConfig
            self._packs_config_cache = PacksConfig(repo_root=self.project_root)
        return self._packs_config_cache.active_packs

    # =========================================================================
    # YAML Loading Utilities (from CompositionBase pattern)
    # =========================================================================

    def load_yaml_safe(self, path: Path) -> Dict[str, Any]:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def merge_yaml(
        self,
        base: Dict[str, Any],
        path: Path,
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge YAML file into base dict."""
        data = self.load_yaml_safe(path)
        if key:
            data = data.get(key, {}) or {}
        if not data:
            return base
        return self.cfg_mgr.deep_merge(base, data)

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

    # ---------- Entity Interface ----------

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
