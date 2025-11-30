"""Layer discovery for composition.

Discovers entities across Core → Packs → Project layers.

Directory conventions:
- Core:           {config}/{type}/{name}.md
- Pack overlays:  {packs}/{pack}/{type}/overlays/{name}.md
- Pack new:       {packs}/{pack}/{type}/{name}.md
- Project overlay:{project}/{type}/overlays/{name}.md
- Project new:    {project}/{type}/{name}.md
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Set

from .errors import CompositionValidationError


@dataclass
class LayerSource:
    """A discovered source file with layer info."""
    path: Path
    layer: str  # "core" | "pack:{name}" | "project"
    is_overlay: bool
    entity_name: str


class LayerDiscovery:
    """Discover entities across composition layers.
    
    Validates:
    - Overlays must reference existing entities
    - New entities must not shadow existing ones
    """
    
    def __init__(
        self,
        content_type: str,
        core_dir: Path,
        packs_dir: Path,
        project_dir: Path,
    ) -> None:
        self.content_type = content_type
        self.core_dir = core_dir
        self.packs_dir = packs_dir
        self.project_dir = project_dir
    
    def discover_core(self) -> Dict[str, LayerSource]:
        """Discover all core entity definitions."""
        entities: Dict[str, LayerSource] = {}
        type_dir = self.core_dir / self.content_type
        
        if not type_dir.exists():
            return entities
        
        # Support both flat and nested structures
        for path in type_dir.rglob("*.md"):
            # Skip files in overlays/ (shouldn't exist in core, but be safe)
            if "overlays" in path.parts:
                continue
            name = path.stem
            if name.startswith("_"):
                continue
            entities[name] = LayerSource(
                path=path,
                layer="core",
                is_overlay=False,
                entity_name=name,
            )
        
        return entities
    
    def discover_pack_overlays(
        self,
        pack: str,
        existing: Set[str],
    ) -> Dict[str, LayerSource]:
        """Discover pack overlays (must reference existing entities)."""
        entities: Dict[str, LayerSource] = {}
        overlays_dir = self.packs_dir / pack / self.content_type / "overlays"
        
        if not overlays_dir.exists():
            return entities
        
        for path in overlays_dir.glob("*.md"):
            name = path.stem
            if name.startswith("_"):
                continue
            
            # Validate: overlay must reference existing entity
            if name not in existing:
                raise CompositionValidationError(
                    f"Pack overlay '{path}' references non-existent {self.content_type} '{name}'.\n"
                    f"Available {self.content_type}: {sorted(existing)}\n"
                    f"To create a NEW {self.content_type}, place the file in "
                    f"'{self.packs_dir / pack / self.content_type}/' (not overlays/)."
                )
            
            entities[name] = LayerSource(
                path=path,
                layer=f"pack:{pack}",
                is_overlay=True,
                entity_name=name,
            )
        
        return entities
    
    def discover_pack_new(
        self,
        pack: str,
        existing: Set[str],
    ) -> Dict[str, LayerSource]:
        """Discover new pack-defined entities (must NOT shadow existing)."""
        entities: Dict[str, LayerSource] = {}
        type_dir = self.packs_dir / pack / self.content_type
        
        if not type_dir.exists():
            return entities
        
        for path in type_dir.glob("*.md"):
            # Skip files in overlays/
            if "overlays" in path.parts:
                continue
            
            name = path.stem
            if name.startswith("_"):
                continue
            
            # Validate: new entity must NOT shadow existing
            if name in existing:
                raise CompositionValidationError(
                    f"Pack file '{path}' shadows existing {self.content_type} '{name}'.\n"
                    f"To extend an existing {self.content_type}, place the file in "
                    f"'{self.packs_dir / pack / self.content_type}/overlays/'.\n"
                    f"To create a NEW {self.content_type}, use a unique name."
                )
            
            entities[name] = LayerSource(
                path=path,
                layer=f"pack:{pack}",
                is_overlay=False,
                entity_name=name,
            )
        
        return entities
    
    def discover_project_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover project overlays (must reference existing entities)."""
        entities: Dict[str, LayerSource] = {}
        overlays_dir = self.project_dir / self.content_type / "overlays"
        
        if not overlays_dir.exists():
            return entities
        
        for path in overlays_dir.glob("*.md"):
            name = path.stem
            if name.startswith("_"):
                continue
            
            # Validate: overlay must reference existing entity
            if name not in existing:
                raise CompositionValidationError(
                    f"Project overlay '{path}' references non-existent {self.content_type} '{name}'.\n"
                    f"Available {self.content_type}: {sorted(existing)}\n"
                    f"To create a NEW {self.content_type}, place the file in "
                    f"'{self.project_dir / self.content_type}/' (not overlays/)."
                )
            
            entities[name] = LayerSource(
                path=path,
                layer="project",
                is_overlay=True,
                entity_name=name,
            )
        
        return entities
    
    def discover_project_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new project-defined entities (must NOT shadow existing)."""
        entities: Dict[str, LayerSource] = {}
        type_dir = self.project_dir / self.content_type
        
        if not type_dir.exists():
            return entities
        
        for path in type_dir.glob("*.md"):
            # Skip files in overlays/
            if "overlays" in path.parts:
                continue
            
            name = path.stem
            if name.startswith("_"):
                continue
            
            # Validate: new entity must NOT shadow existing
            if name in existing:
                raise CompositionValidationError(
                    f"Project file '{path}' shadows existing {self.content_type} '{name}'.\n"
                    f"To extend an existing {self.content_type}, place the file in "
                    f"'{self.project_dir / self.content_type}/overlays/'.\n"
                    f"To create a NEW {self.content_type}, use a unique name."
                )
            
            entities[name] = LayerSource(
                path=path,
                layer="project",
                is_overlay=False,
                entity_name=name,
            )
        
        return entities




