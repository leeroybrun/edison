"""Layered composer for unified composition system.

Composes content from Core → Packs → Project layers using
section-based composition with HTML comment markers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

from edison.core.utils.paths import PathResolver

from .discovery import LayerDiscovery, LayerSource
from .errors import CompositionValidationError
from .paths import CompositionPathResolver
from .schema import CompositionSchema
from .sections import (
    SectionComposer,
    SectionMode,
    SectionParser,
    SectionRegistry,
)


class LayeredComposer:
    """Unified layered composer for all content types.
    
    Handles:
    - Discovery of entities across layers (Core → Packs → Project)
    - Validation of overlay/new entity placement
    - Section parsing and registry management
    - Final composition
    
    Unified directory conventions:
    - Core:           {config}/{type}/{name}.md
    - Pack overlays:  {packs}/{pack}/{type}/overlays/{name}.md
    - Pack new:       {packs}/{pack}/{type}/{name}.md (NOT in overlays/)
    - Project overlay:{project}/{type}/overlays/{name}.md
    - Project new:    {project}/{type}/{name}.md (NOT in overlays/)
    """
    
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        content_type: str = "agents",
    ) -> None:
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.content_type = content_type
        
        # Use composition path resolver (SINGLE SOURCE OF TRUTH)
        path_resolver = CompositionPathResolver(self.repo_root, content_type)
        self.core_dir = path_resolver.core_dir
        self.packs_dir = path_resolver.packs_dir
        self.project_dir = path_resolver.project_dir
        
        # Initialize components
        self.schema = CompositionSchema.load()
        self.discovery = LayerDiscovery(
            content_type=content_type,
            core_dir=self.core_dir,
            packs_dir=self.packs_dir,
            project_dir=self.project_dir,
        )
        self.parser = SectionParser()
        self.section_composer = SectionComposer()
    
    # -------------------------------------------------------------------------
    # Discovery (delegate to LayerDiscovery)
    # -------------------------------------------------------------------------
    
    def discover_core(self) -> Dict[str, LayerSource]:
        """Discover all core entity definitions."""
        return self.discovery.discover_core()
    
    def discover_pack_overlays(self, pack: str, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover pack overlays (must reference existing entities)."""
        return self.discovery.discover_pack_overlays(pack, existing)
    
    def discover_pack_new(self, pack: str, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new pack-defined entities (must NOT shadow existing)."""
        return self.discovery.discover_pack_new(pack, existing)
    
    def discover_project_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover project overlays (must reference existing entities)."""
        return self.discovery.discover_project_overlays(existing)
    
    def discover_project_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new project-defined entities (must NOT shadow existing)."""
        return self.discovery.discover_project_new(existing)
    
    # -------------------------------------------------------------------------
    # Composition
    # -------------------------------------------------------------------------
    
    def _init_registry(self) -> SectionRegistry:
        """Initialize section registry with known sections from schema."""
        known_sections = self.schema.get_known_sections(self.content_type)
        return SectionRegistry(
            known_sections={name: [] for name in known_sections},
            extensible_sections={},
            append_sections=[],
        )
    
    def _process_overlay(
        self,
        source: LayerSource,
        registry: SectionRegistry,
    ) -> None:
        """Parse overlay file and add sections to registry."""
        content = source.path.read_text(encoding="utf-8")
        sections = self.parser.parse(content, source.layer)
        
        for section in sections:
            if section.mode == SectionMode.EXTEND:
                registry.add_extension(section.name, section.content)
            elif section.mode == SectionMode.NEW_SECTION:
                registry.add_new_section(section.name, section.content)
            elif section.mode == SectionMode.APPEND:
                registry.add_append(section.content)
    
    def compose(self, name: str, packs: List[str]) -> str:
        """Compose a single entity from all layers.
        
        Args:
            name: Entity name (e.g., "api-builder")
            packs: List of active pack names
        
        Returns:
            Composed Markdown content
        """
        # 1. Discover core
        core_entities = self.discover_core()
        if name not in core_entities:
            raise CompositionValidationError(
                f"Core {self.content_type} '{name}' not found.\n"
                f"Available: {sorted(core_entities.keys())}"
            )
        
        core_source = core_entities[name]
        template = core_source.path.read_text(encoding="utf-8")
        
        # 2. Initialize registry with known sections
        registry = self._init_registry()
        
        # 3. Collect all existing names (core + pack-new from earlier packs)
        existing: Set[str] = set(core_entities.keys())
        
        # 4. Process pack layers in order
        for pack in packs:
            # Get pack overlays for this entity
            pack_overlays = self.discover_pack_overlays(pack, existing)
            if name in pack_overlays:
                self._process_overlay(pack_overlays[name], registry)
            
            # Discover pack-new entities (updates existing set)
            pack_new = self.discover_pack_new(pack, existing)
            existing.update(pack_new.keys())
        
        # 5. Process project overlay
        project_overlays = self.discover_project_overlays(existing)
        if name in project_overlays:
            self._process_overlay(project_overlays[name], registry)
        
        # 6. Compose final output
        return self.section_composer.compose(template, registry)
    
    def compose_all(self, packs: List[str]) -> Dict[str, str]:
        """Compose all entities (core + pack-new + project-new).
        
        Returns:
            Dict mapping entity name to composed content
        """
        results: Dict[str, str] = {}
        
        # Discover all entities across layers
        core = self.discover_core()
        existing = set(core.keys())
        
        all_entities: Dict[str, LayerSource] = dict(core)
        
        # Add pack-new entities
        for pack in packs:
            pack_new = self.discover_pack_new(pack, existing)
            all_entities.update(pack_new)
            existing.update(pack_new.keys())
        
        # Add project-new entities
        project_new = self.discover_project_new(existing)
        all_entities.update(project_new)
        
        # Compose each
        for entity_name in all_entities:
            try:
                results[entity_name] = self.compose(entity_name, packs)
            except CompositionValidationError:
                # Skip entities that can't be composed (e.g., pack-new without template)
                # For pack-new/project-new, the file IS the content
                source = all_entities[entity_name]
                if not source.is_overlay:
                    results[entity_name] = source.path.read_text(encoding="utf-8")
        
        return results




