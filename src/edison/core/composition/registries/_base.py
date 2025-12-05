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

from pathlib import Path
from typing import Any, ClassVar, Dict, Generic, List, Optional, TypeVar

from ..core.base import CompositionBase
from ..core.discovery import LayerDiscovery
from ..strategies import (
    CompositionContext,
    LayerContent,
    MarkdownCompositionStrategy,
)

# Type variable for registry content types
T = TypeVar("T")


# Fallback defaults if YAML config not available
# These are overridden by composition.yaml > defaults section
_FALLBACK_STRATEGY_CONFIG: Dict[str, Any] = {
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
    _comp_config_cache: Optional["CompositionConfig"] = None  # type: ignore[name-defined]

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize composable registry.

        Args:
            project_root: Project root directory. Resolved automatically if not provided.

        Raises:
            NotImplementedError: If content_type is not defined by subclass.
        """
        super().__init__(project_root)
    
    @property
    def comp_config(self) -> "CompositionConfig":  # type: ignore[name-defined]
        """Lazy-initialized CompositionConfig for typed config access."""
        if self._comp_config_cache is None:
            from edison.core.config.domains.composition import CompositionConfig
            self._comp_config_cache = CompositionConfig(repo_root=self.project_root)
        return self._comp_config_cache

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
                file_pattern=self.file_pattern,
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
                file_pattern=self.file_pattern,
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

        Priority order (lowest to highest):
        1. _FALLBACK_STRATEGY_CONFIG (code defaults)
        2. composition.defaults section (via CompositionConfig)
        3. composition.content_types.{type} section (via CompositionConfig)
        4. Class-level strategy_config attribute

        Returns:
            Strategy configuration dict
        """
        # Start with code fallback defaults
        result = dict(_FALLBACK_STRATEGY_CONFIG)

        # Layer 2: Read defaults from CompositionConfig
        defaults = self.comp_config.defaults
        if defaults:
            dedupe_cfg = defaults.get("dedupe", {}) or {}
            if "shingle_size" in dedupe_cfg:
                result["dedupe_shingle_size"] = dedupe_cfg["shingle_size"]
            if "min_shingles" in dedupe_cfg:
                result["dedupe_min_shingles"] = dedupe_cfg["min_shingles"]

        # Layer 3: Read content-type specific config from CompositionConfig
        type_cfg = self.comp_config.get_content_type(self.content_type)
        if type_cfg:
            # Dedupe config
            if type_cfg.dedupe:
                result["enable_dedupe"] = True
            if type_cfg.composition_mode == "concatenate":
                result["enable_sections"] = False  # Concatenate doesn't use sections

        # Layer 4: Class-level strategy_config overrides
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

        # Get custom context vars from subclass (for data-driven templates)
        context_vars = self.get_context_vars(name, packs)

        # Create composition context with custom vars
        context = CompositionContext(
            active_packs=packs,
            config=self.config,
            project_root=self.project_root,
            context_vars=context_vars,
        )

        # Compose using strategy
        composed = self.strategy.compose(layers, context)

        # Post-process
        return self._post_compose(name, composed)
    
    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        """Get context variables for template substitution.
        
        Provides built-in variables and can be extended in subclasses
        for data-driven templates (like {{#each}} loops).
        
        Built-in variables (always available):
            - name: Entity name being composed
            - content_type: Content type (e.g., "agents", "constitutions")
            - source_layers: "core + pack(x) + pack(y)"
            - timestamp: ISO8601 timestamp
            - generated_date: Same as timestamp (alias)
            - version: Project version from config
            - template: Source template path "{content_type}/{name}.md"
            - output_dir: Output directory from config (resolved)
            - output_path: Full output file path (resolved)
            - PROJECT_EDISON_DIR: Project .edison directory path
        
        Override in subclasses to add custom variables.
        
        Args:
            name: Entity name being composed
            packs: Active pack names
            
        Returns:
            Dict of context variables for template substitution
        """
        from edison.core.utils.time import utc_timestamp
        from edison.core.composition.output.headers import resolve_version
        
        timestamp = utc_timestamp()
        source_layers = ["core"] + [f"pack({p})" for p in packs]
        version = resolve_version(self.cfg_mgr, self.config)
        
        # Get output paths from config (relative to project root)
        project_edison_dir = str(self.project_dir.relative_to(self.project_root))
        output_dir, output_path = self._resolve_output_paths(name)
        
        return {
            # Entity identification
            "name": name,
            "content_type": self.content_type,
            # Source info
            "source_layers": " + ".join(source_layers),
            "template": f"{self.content_type}/{name}.md",
            # Timestamps
            "timestamp": timestamp,
            "generated_date": timestamp,
            # Version
            "version": str(version),
            # Output paths (resolved from config)
            "output_dir": output_dir,
            "output_path": output_path,
            # Project paths
            "PROJECT_EDISON_DIR": project_edison_dir,
        }

    def _resolve_output_paths(self, name: str) -> tuple[str, str]:
        """Resolve output directory and file path from config.
        
        Returns paths relative to project root.
        Uses CompositionConfig for typed config access.
        
        Args:
            name: Entity name
            
        Returns:
            Tuple of (output_dir, output_path) - both relative to project root
        """
        # Get content type config from CompositionConfig
        type_cfg = self.comp_config.get_content_type(self.content_type)
        
        if type_cfg:
            output_path_template = type_cfg.output_path or f"{{{{PROJECT_EDISON_DIR}}}}/_generated/{self.content_type}"
            filename_pattern = type_cfg.filename_pattern or "{name}.md"
        else:
            # Fallback defaults
            output_path_template = f"{{{{PROJECT_EDISON_DIR}}}}/_generated/{self.content_type}"
            filename_pattern = "{name}.md"
        
        # Resolve PROJECT_EDISON_DIR to relative path
        project_edison_rel = str(self.project_dir.relative_to(self.project_root))
        output_dir = output_path_template.replace("{{PROJECT_EDISON_DIR}}", project_edison_rel)
        
        # Resolve filename pattern
        filename = filename_pattern.replace("{name}", name).replace("{NAME}", name.upper())
        output_path = f"{output_dir}/{filename}"
        
        return output_dir, output_path

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
            # Overlays should ALWAYS be applied - they extend existing entities
            if name in project_over:
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
]
