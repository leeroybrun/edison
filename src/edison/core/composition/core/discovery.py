"""Layer discovery for composition.

Discovers entities across Core → Packs → User → Project layers.

Directory conventions:
- Core:           {config}/{type}/{name}.md
- Pack overlays:  {packs_root}/{pack}/{type}/overlays/{name}.md
- Pack new:       {packs_root}/{pack}/{type}/{name}.md
- User overlay:   {user}/{type}/overlays/{name}.md
- User new:       {user}/{type}/{name}.md
- Project overlay:{project}/{type}/overlays/{name}.md
- Project new:    {project}/{type}/{name}.md
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
        pack_roots: List[Tuple[str, Path]],
        user_dir: Path,
        project_dir: Path,
        file_pattern: str = "*.md",
        *,
        exclude_globs: Optional[List[str]] = None,
    ) -> None:
        self.content_type = content_type
        self.core_dir = core_dir
        # Pack roots in low→high precedence order (bundled → user → project).
        self.pack_roots = list(pack_roots)
        self.user_dir = user_dir
        self.project_dir = project_dir
        self.file_pattern = file_pattern
        self.exclude_globs = list(exclude_globs or [])
        self._core_cache: Optional[Dict[str, LayerSource]] = None
        self._pack_new_cache: Dict[Tuple[str, str], Dict[str, LayerSource]] = {}
        self._pack_overlay_cache: Dict[Tuple[str, str], Dict[str, LayerSource]] = {}
        self._user_new_cache: Optional[Dict[str, LayerSource]] = None
        self._user_overlay_cache: Optional[Dict[str, LayerSource]] = None
        self._project_new_cache: Optional[Dict[str, LayerSource]] = None
        self._project_overlay_cache: Optional[Dict[str, LayerSource]] = None

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
        if self._core_cache is not None:
            return dict(self._core_cache)

        entities: Dict[str, LayerSource] = {}
        type_dir = self.core_dir / self.content_type
        
        if not type_dir.exists():
            self._core_cache = entities
            return dict(entities)
        
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
        
        self._core_cache = entities
        return dict(entities)

    def _scan_pack_new(self, pack_root: Path, pack: str, kind: str) -> Dict[str, LayerSource]:
        cache_key = (kind, pack)
        cached = self._pack_new_cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        entities: Dict[str, LayerSource] = {}
        type_dir = pack_root / pack / self.content_type
        if not type_dir.exists():
            self._pack_new_cache[cache_key] = entities
            return dict(entities)

        for path in type_dir.rglob(self.file_pattern):
            if "overlays" in path.parts:
                continue
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=f"pack:{pack}",
                is_overlay=False,
                entity_name=name,
            )

        self._pack_new_cache[cache_key] = entities
        return dict(entities)

    def _scan_pack_overlays(self, pack_root: Path, pack: str, kind: str) -> Dict[str, LayerSource]:
        cache_key = (kind, pack)
        cached = self._pack_overlay_cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        entities: Dict[str, LayerSource] = {}
        overlays_dir = pack_root / pack / self.content_type / "overlays"
        if not overlays_dir.exists():
            self._pack_overlay_cache[cache_key] = entities
            return dict(entities)

        for path in overlays_dir.rglob(self.file_pattern):
            if self._is_excluded(overlays_dir, path):
                continue
            name = self._entity_key(overlays_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=f"pack:{pack}",
                is_overlay=True,
                entity_name=name,
            )

        self._pack_overlay_cache[cache_key] = entities
        return dict(entities)

    def iter_pack_layers(
        self,
        pack: str,
        existing: Set[str],
    ) -> List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]]:
        """Discover pack new+overlay sources across all pack roots in precedence order.

        Mutates ``existing`` to include newly discovered pack-defined entities so
        later roots and overlays can reference them.
        """
        results: List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]] = []

        for kind, pack_root in self.pack_roots:
            new_map = self._scan_pack_new(pack_root, pack, kind)
            # Validate: pack new must NOT shadow existing.
            for name, src in new_map.items():
                if name in existing:
                    raise CompositionValidationError(
                        f"Pack file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                        f"To extend an existing {self.content_type}, place the file in "
                        f"'{pack_root / pack / self.content_type}/overlays/'.\n"
                        f"To create a NEW {self.content_type}, use a unique name."
                    )
            existing.update(new_map.keys())

            over_map = self._scan_pack_overlays(pack_root, pack, kind)
            # Validate: overlays must reference existing entities.
            for name, src in over_map.items():
                if name not in existing:
                    raise CompositionValidationError(
                        f"Pack overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                        f"Available {self.content_type}: {sorted(existing)}\n"
                        f"To create a NEW {self.content_type}, place the file in "
                        f"'{pack_root / pack / self.content_type}/' (not overlays/)."
                    )

            results.append((kind, new_map, over_map))

        return results

    def _scan_layer_new(self, base: Path, *, label: str, cache_key: str) -> Dict[str, LayerSource]:
        cache_attr = f"_{cache_key}_new_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            return dict(cached)

        entities: Dict[str, LayerSource] = {}
        type_dir = base / self.content_type
        if not type_dir.exists():
            setattr(self, cache_attr, entities)
            return dict(entities)

        for path in type_dir.rglob(self.file_pattern):
            if "overlays" in path.parts:
                continue
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=label,
                is_overlay=False,
                entity_name=name,
            )

        setattr(self, cache_attr, entities)
        return dict(entities)

    def _scan_layer_overlays(self, base: Path, *, label: str, cache_key: str) -> Dict[str, LayerSource]:
        cache_attr = f"_{cache_key}_overlay_cache"
        cached = getattr(self, cache_attr, None)
        if cached is not None:
            return dict(cached)

        entities: Dict[str, LayerSource] = {}
        overlays_dir = base / self.content_type / "overlays"
        if not overlays_dir.exists():
            setattr(self, cache_attr, entities)
            return dict(entities)

        for path in overlays_dir.rglob(self.file_pattern):
            if self._is_excluded(overlays_dir, path):
                continue
            name = self._entity_key(overlays_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=label,
                is_overlay=True,
                entity_name=name,
            )

        setattr(self, cache_attr, entities)
        return dict(entities)

    def discover_user_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new user-defined entities (must NOT shadow existing)."""
        new_map = self._scan_layer_new(self.user_dir, label="user", cache_key="user")
        for name, src in new_map.items():
            if name in existing:
                raise CompositionValidationError(
                    f"User file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                    f"To extend an existing {self.content_type}, place the file in "
                    f"'{(self.user_dir / self.content_type) / 'overlays'}'.\n"
                    f"To create a NEW {self.content_type}, use a unique name."
                )
        return new_map

    def discover_user_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover user overlays (must reference existing entities)."""
        over_map = self._scan_layer_overlays(self.user_dir, label="user", cache_key="user")
        for name, src in over_map.items():
            if name not in existing:
                raise CompositionValidationError(
                    f"User overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                    f"Available {self.content_type}: {sorted(existing)}\n"
                    f"To create a NEW {self.content_type}, place the file in "
                    f"'{self.user_dir / self.content_type}/' (not overlays/)."
                )
        return over_map
    
    def discover_project_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover project overlays (must reference existing entities)."""
        over_map = self._scan_layer_overlays(self.project_dir, label="project", cache_key="project")
        for name, src in over_map.items():
            if name not in existing:
                raise CompositionValidationError(
                    f"Project overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                    f"Available {self.content_type}: {sorted(existing)}\n"
                    f"To create a NEW {self.content_type}, place the file in "
                    f"'{self.project_dir / self.content_type}/' (not overlays/)."
                )
        return over_map
    
    def discover_project_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new project-defined entities (must NOT shadow existing)."""
        new_map = self._scan_layer_new(self.project_dir, label="project", cache_key="project")
        for name, src in new_map.items():
            if name in existing:
                raise CompositionValidationError(
                    f"Project file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                    f"To extend an existing {self.content_type}, place the file in "
                    f"'{(self.project_dir / self.content_type) / 'overlays'}'.\n"
                    f"To create a NEW {self.content_type}, use a unique name."
                )
        return new_map

