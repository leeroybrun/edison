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
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Optional

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
        file_pattern: str = "*.md",
        *,
        exclude_globs: Optional[List[str]] = None,
    ) -> None:
        self.content_type = content_type
        self.core_dir = core_dir
        self.packs_dir = packs_dir
        self.project_dir = project_dir
        self.file_pattern = file_pattern
        self.exclude_globs = list(exclude_globs or [])

    def _entity_key(self, base_dir: Path, file_path: Path) -> str:
        """Derive a stable entity key relative to base_dir.

        Keys preserve subdirectories, enabling arbitrary nesting:
          <base>/shared/CONTEXT7.md -> "shared/CONTEXT7"
        """
        rel = file_path.relative_to(base_dir)
        return rel.with_suffix("").as_posix()

    def _is_excluded(self, base_dir: Path, file_path: Path) -> bool:
        """Return True if file_path should be excluded for this content type."""
        if not self.exclude_globs:
            return False

        rel = file_path.relative_to(base_dir).as_posix()
        for pat in self.exclude_globs:
            # Patterns are evaluated against relative POSIX path.
            if fnmatch(rel, pat):
                return True
        return False
    
    def discover_core(self) -> Dict[str, LayerSource]:
        """Discover all core entity definitions."""
        entities: Dict[str, LayerSource] = {}
        type_dir = self.core_dir / self.content_type
        
        if not type_dir.exists():
            return entities
        
        # Support both flat and nested structures
        for path in type_dir.rglob(self.file_pattern):
            # Skip files in overlays/ (shouldn't exist in core, but be safe)
            if "overlays" in path.parts:
                continue
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
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
        
        for path in overlays_dir.rglob(self.file_pattern):
            if self._is_excluded(overlays_dir, path):
                continue
            name = self._entity_key(overlays_dir, path)
            
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
        
        for path in type_dir.rglob(self.file_pattern):
            # Skip files in overlays/
            if "overlays" in path.parts:
                continue
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
            
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
        
        for path in overlays_dir.rglob(self.file_pattern):
            if self._is_excluded(overlays_dir, path):
                continue
            name = self._entity_key(overlays_dir, path)
            
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
        
        for path in type_dir.rglob(self.file_pattern):
            # Skip files in overlays/
            if "overlays" in path.parts:
                continue
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
            
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


