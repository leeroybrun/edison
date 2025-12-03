"""Composable registry base class for file-based content composition.

ComposableRegistry is the unified base class for ALL file-based registries:
- Uses LayerDiscovery for file discovery
- Uses MarkdownCompositionStrategy for composition
- Subclasses define: content_type, file_pattern, strategy_config

All registries (agents, validators, guidelines, constitutions, documents)
extend this class with their specific configurations.

Architecture:
    CompositionBase (provides path resolution, config, YAML utilities)
    └── ComposableRegistry (this module)
        ├── AgentRegistry
        ├── ValidatorRegistry
        ├── GuidelineRegistry
        ├── ConstitutionRegistry
        └── DocumentTemplateRegistry
"""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, Generic, List, Optional, TypeVar

from edison.core.composition.core.base import CompositionBase
from edison.core.composition.core.discovery import LayerDiscovery, LayerSource
from edison.core.composition.strategies import (
    CompositionContext,
    LayerContent,
    MarkdownCompositionStrategy,
)

# Type variable for registry content types
T = TypeVar("T")


# Default strategy configuration
DEFAULT_STRATEGY_CONFIG: Dict[str, Any] = {
    "enable_sections": True,
    "enable_dedupe": False,
    "dedupe_shingle_size": 12,
    "enable_template_processing": True,
}


class ComposableRegistry(CompositionBase, Generic[T]):
    """Abstract base class for composable content registries.

    Uses LayerDiscovery for file discovery across layers (Core → Packs → Project)
    and MarkdownCompositionStrategy for content composition.

    Subclasses MUST define:
        - content_type: String identifier for content (e.g., "agents", "validators")
        - file_pattern: Glob pattern for files (e.g., "*.md")

    Subclasses MAY override:
        - strategy_config: Dict with MarkdownCompositionStrategy options
        - _post_compose(): Hook for post-composition processing

    Type Parameters:
        T: The content type this registry manages (e.g., str, Agent, Validator)

    Example:
        class AgentRegistry(ComposableRegistry[Agent]):
            content_type = "agents"
            file_pattern = "*.md"
            strategy_config = {"enable_sections": True, "enable_dedupe": False}

            def _post_compose(self, name: str, content: str) -> Agent:
                return Agent(name=name, prompt=content)
    """

    # Class attributes - subclasses MUST override
    content_type: ClassVar[str] = ""
    file_pattern: ClassVar[str] = "*.md"

    # Strategy configuration - subclasses MAY override
    strategy_config: ClassVar[Dict[str, Any]] = {}
    # Whether to merge all same-name layers (concatenate) instead of single template + overlays
    merge_same_name: ClassVar[bool] = False

    # Internal state
    _bundled_discovery: Optional[LayerDiscovery] = None
    _project_packs_discovery: Optional[LayerDiscovery] = None
    _strategy: Optional[MarkdownCompositionStrategy] = None

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize composable registry.

        Args:
            project_root: Project root directory. Resolved automatically if not provided.

        Raises:
            NotImplementedError: If content_type is not defined by subclass.
        """
        super().__init__(project_root)

        # Validate required class attributes
        if not self.content_type:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'content_type' class attribute"
            )

    @property
    def bundled_discovery(self) -> LayerDiscovery:
        """Lazy-initialized LayerDiscovery for bundled packs."""
        if self._bundled_discovery is None:
            self._bundled_discovery = LayerDiscovery(
                content_type=self.content_type,
                core_dir=self.core_dir,
                packs_dir=self.bundled_packs_dir,
                project_dir=self.project_dir,
            )
        return self._bundled_discovery

    @property
    def project_packs_discovery(self) -> LayerDiscovery:
        """Lazy-initialized LayerDiscovery for project packs."""
        if self._project_packs_discovery is None:
            self._project_packs_discovery = LayerDiscovery(
                content_type=self.content_type,
                core_dir=self.core_dir,
                packs_dir=self.project_packs_dir,
                project_dir=self.project_dir,
            )
        return self._project_packs_discovery


    @property
    def strategy(self) -> MarkdownCompositionStrategy:
        """Lazy-initialized MarkdownCompositionStrategy instance."""
        if self._strategy is None:
            config = self.get_strategy_config()
            self._strategy = MarkdownCompositionStrategy(
                enable_sections=config.get("enable_sections", True),
                enable_dedupe=config.get("enable_dedupe", False),
                dedupe_shingle_size=config.get("dedupe_shingle_size", 12),
                enable_template_processing=config.get(
                    "enable_template_processing", True
                ),
            )
        return self._strategy

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get merged strategy configuration.

        Merges class-level strategy_config with defaults.

        Returns:
            Strategy configuration dict
        """
        result = dict(DEFAULT_STRATEGY_CONFIG)
        if self.strategy_config:
            result.update(self.strategy_config)
        return result

    # =========================================================================
    # Discovery Interface (delegates to LayerDiscovery)
    # =========================================================================

    def discover_core(self) -> Dict[str, Path]:
        """Discover content from core/bundled sources.

        Returns:
            Dict mapping entity names to file paths from core layer
        """
        entities = self.bundled_discovery.discover_core()
        return {name: source.path for name, source in entities.items()}

    def discover_packs(self, packs: List[str]) -> Dict[str, Path]:
        """Discover content from active packs (bundled AND project).

        Args:
            packs: List of active pack names

        Returns:
            Dict mapping entity names to file paths from pack layers
        """
        result: Dict[str, Path] = {}
        existing = set(self.discover_core().keys())

        for pack in packs:
            # Check bundled packs first
            try:
                pack_new = self.bundled_discovery.discover_pack_new(pack, existing)
                for name, source in pack_new.items():
                    result[name] = source.path
                existing.update(pack_new.keys())
            except Exception:
                pass  # Bundled pack may not exist

            # Then check project packs (can extend bundled or define new)
            try:
                pack_new = self.project_packs_discovery.discover_pack_new(pack, existing)
                for name, source in pack_new.items():
                    result[name] = source.path
                existing.update(pack_new.keys())
            except Exception:
                pass  # Project pack may not exist

        return result

    def discover_project(self) -> Dict[str, Path]:
        """Discover content from project layer.

        Returns:
            Dict mapping entity names to file paths from project layer
        """
        # Get all existing entities first
        existing = set(self.discover_core().keys())
        for pack in self.get_active_packs():
            pack_new = self.bundled_discovery.discover_pack_new(pack, existing)
            existing.update(pack_new.keys())

        # Discover project-new entities
        project_new = self.bundled_discovery.discover_project_new(existing)
        return {name: source.path for name, source in project_new.items()}

    def discover_all(self, packs: Optional[List[str]] = None) -> Dict[str, Path]:
        """Discover all content across all layers.

        Args:
            packs: Optional list of active pack names (uses get_active_packs() if None)

        Returns:
            Dict mapping entity names to file paths
        """
        packs = packs or self.get_active_packs()
        result: Dict[str, Path] = {}

        # Core layer
        result.update(self.discover_core())

        # Pack layers (new + overlays, bundled and project packs)
        existing = set(result.keys())
        for pack in packs:
            pack_new = self.bundled_discovery.discover_pack_new(pack, existing)
            for name, source in pack_new.items():
                result[name] = source.path
            existing.update(pack_new.keys())

            pack_over = self.bundled_discovery.discover_pack_overlays(pack, existing)
            for name, source in pack_over.items():
                result[name] = source.path
            existing.update(pack_over.keys())

            pack_new = self.project_packs_discovery.discover_pack_new(pack, existing)
            for name, source in pack_new.items():
                result[name] = source.path
            existing.update(pack_new.keys())

            pack_over = self.project_packs_discovery.discover_pack_overlays(
                pack, existing
            )
            for name, source in pack_over.items():
                result[name] = source.path
            existing.update(pack_over.keys())

        # Project layer (new + overlays)
        project_new = self.bundled_discovery.discover_project_new(existing)
        for name, source in project_new.items():
            result[name] = source.path
        existing.update(project_new.keys())

        project_over = self.bundled_discovery.discover_project_overlays(existing)
        for name, source in project_over.items():
            result[name] = source.path
        existing.update(project_over.keys())

        return result

    # =========================================================================
    # Composition Interface
    # =========================================================================

    def compose(
        self,
        name: str,
        packs: Optional[List[str]] = None,
    ) -> Optional[T]:
        """Compose a single entity from all layers.

        Uses MarkdownCompositionStrategy for composition with section/extend
        markers and optional deduplication.

        Args:
            name: Entity name to compose
            packs: Optional list of active pack names

        Returns:
            Composed entity or None if not found
        """
        packs = packs or self.get_active_packs()

        # Gather layer content
        layers = self._gather_layers(name, packs)

        if not layers:
            return None

        # Create composition context
        context = CompositionContext(
            active_packs=packs,
            config=self.config,
            project_root=self.project_root,
        )

        # Compose using strategy
        composed = self.strategy.compose(layers, context)

        # Post-process
        return self._post_compose(name, composed)

    def compose_all(
        self,
        packs: Optional[List[str]] = None,
    ) -> Dict[str, T]:
        """Compose all entities across all layers.

        Args:
            packs: Optional list of active pack names

        Returns:
            Dict mapping entity names to composed entities
        """
        packs = packs or self.get_active_packs()
        all_entities = self.discover_all(packs)

        results: Dict[str, T] = {}
        for name in all_entities:
            composed = self.compose(name, packs)
            if composed is not None:
                results[name] = composed

        return results

    def _gather_layers(
        self,
        name: str,
        packs: List[str],
    ) -> List[LayerContent]:
        """Gather content from all layers for an entity.

        Args:
            name: Entity name
            packs: List of active pack names

        Returns:
            List of LayerContent in order (core → packs → project)
        """
        layers: List[LayerContent] = []

        # Discover core entities
        core_entities = self.bundled_discovery.discover_core()
        existing = set(core_entities.keys())

        # Always include core if present
        if name in core_entities:
            path = core_entities[name].path
            content = path.read_text(encoding="utf-8")
            layers.append(LayerContent(content=content, source="core", path=path))

        # Helper to append if present
        def _append(source_path: Path, source_label: str) -> None:
            if source_path and source_path.exists():
                content = source_path.read_text(encoding="utf-8")
                layers.append(LayerContent(content=content, source=source_label, path=source_path))

        # Packs (bundled + project)
        for pack in packs:
            # bundled new
            try:
                pack_new = self.bundled_discovery.discover_pack_new(pack, existing)
                if name in pack_new and (self.merge_same_name or name not in core_entities):
                    _append(pack_new[name].path, f"pack:{pack}")
                existing.update(pack_new.keys())
            except Exception:
                pass

            # bundled overlays
            try:
                pack_over = self.bundled_discovery.discover_pack_overlays(pack, existing)
                if name in pack_over:
                    _append(pack_over[name].path, f"pack:{pack}")
            except Exception:
                pass

            # project pack new
            try:
                pack_new = self.project_packs_discovery.discover_pack_new(pack, existing)
                if name in pack_new and (self.merge_same_name or name not in core_entities):
                    _append(pack_new[name].path, f"pack:{pack}")
                existing.update(pack_new.keys())
            except Exception:
                pass

            # project pack overlays
            try:
                pack_over = self.project_packs_discovery.discover_pack_overlays(pack, existing)
                if name in pack_over:
                    _append(pack_over[name].path, f"pack:{pack}")
            except Exception:
                pass

        # Project layer (new + overlays)
        try:
            project_new = self.bundled_discovery.discover_project_new(existing)
            if name in project_new and (self.merge_same_name or name not in core_entities):
                _append(project_new[name].path, "project")
            existing.update(project_new.keys())
        except Exception:
            pass

        try:
            project_over = self.bundled_discovery.discover_project_overlays(existing)
            if name in project_over and (self.merge_same_name or name not in core_entities):
                _append(project_over[name].path, "project")
        except Exception:
            pass

        # When merge_same_name is enabled, allow project same-name file even if discover_project_new skipped it
        if self.merge_same_name:
            project_root_dir = self.project_dir / self.content_type
            if project_root_dir.exists():
                for candidate in project_root_dir.rglob(f"{name}.md"):
                    if candidate.is_file() and all(l.path != candidate for l in layers):
                        _append(candidate, "project")

        return layers

    def _post_compose(self, name: str, content: str) -> T:
        """Post-process composed content.

        Override in subclasses to transform composed string into entity type.
        Default implementation returns content as-is (assumes T is str).

        Args:
            name: Entity name
            content: Composed markdown content

        Returns:
            Entity of type T
        """
        return content  # type: ignore[return-value]

    # =========================================================================
    # Standard Registry Interface
    # =========================================================================

    def exists(self, name: str) -> bool:
        """Check if an entity exists in any layer.

        Args:
            name: Entity name

        Returns:
            True if entity exists
        """
        all_entities = self.discover_all()
        return name in all_entities

    def get(self, name: str) -> Optional[T]:
        """Get an entity by name.

        Alias for compose() with active packs.

        Args:
            name: Entity name

        Returns:
            Composed entity or None
        """
        return self.compose(name)

    def get_all(self) -> List[T]:
        """Get all entities.

        Returns:
            List of all composed entities
        """
        return list(self.compose_all().values())

    def list_names(self, packs: Optional[List[str]] = None) -> List[str]:
        """List all entity names.

        Args:
            packs: Optional list of active pack names

        Returns:
            Sorted list of entity names
        """
        return sorted(self.discover_all(packs).keys())


__all__ = [
    "ComposableRegistry",
    "DEFAULT_STRATEGY_CONFIG",
]
