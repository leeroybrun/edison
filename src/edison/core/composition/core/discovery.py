"""Layer discovery for composition.

Discovers entities across Core → Packs → N overlay layers.

Directory conventions:
- Core:           {config}/{type}/{name}.md
- Pack overlays:  {packs_root}/{pack}/{type}/overlays/{name}.md
- Pack new:       {packs_root}/{pack}/{type}/{name}.md
- Layer overlay:   {layer_root}/{type}/overlays/{name}.md
- Layer new:       {layer_root}/{type}/{name}.md
"""
from __future__ import annotations

import os
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
    - New entities are those that do not exist in lower-precedence layers

    Convention:
    - Files at `{layer}/{type}/{name}.md` define NEW entities (must be unique).
    - Files at `{layer}/{type}/overlays/{name}.md` overlay existing entities.
    """
    
    def __init__(
        self,
        content_type: str,
        core_dir: Path,
        pack_roots: List[Tuple[str, Path]],
        overlay_layers: Optional[List[Tuple[str, Path]]] = None,
        file_pattern: str = "*.md",
        *,
        user_dir: Optional[Path] = None,
        project_dir: Optional[Path] = None,
        exclude_globs: Optional[List[str]] = None,
        allow_shadowing: bool = False,
        vendor_roots: Optional[List[Tuple[str, Path]]] = None,
    ) -> None:
        self.content_type = content_type
        self.core_dir = core_dir
        # Vendor roots in low→high precedence order.
        # Precedence: core < vendors < packs < overlay layers.
        self.vendor_roots = list(vendor_roots or [])
        # Pack roots in low→high precedence order (bundled → user → project).
        self.pack_roots = list(pack_roots)
        # Overlay layers in low→high precedence order (e.g., company → user → project).
        # Backwards compatible: allow callers to pass user_dir/project_dir instead of overlay_layers.
        if overlay_layers is None:
            inferred: List[Tuple[str, Path]] = []
            if user_dir is not None:
                inferred.append(("user", user_dir))
            if project_dir is not None:
                inferred.append(("project", project_dir))
            overlay_layers = inferred
        self.overlay_layers = list(overlay_layers)
        self.file_pattern = file_pattern
        self.exclude_globs = list(exclude_globs or [])
        self.allow_shadowing = allow_shadowing
        self._core_cache: Optional[Dict[str, LayerSource]] = None
        self._vendor_new_cache: Dict[str, Dict[str, LayerSource]] = {}
        self._vendor_overlay_cache: Dict[str, Dict[str, LayerSource]] = {}
        self._pack_new_cache: Dict[Tuple[str, str], Dict[str, LayerSource]] = {}
        self._pack_overlay_cache: Dict[Tuple[str, str], Dict[str, LayerSource]] = {}
        self._layer_new_cache: Dict[str, Dict[str, LayerSource]] = {}
        self._layer_overlay_cache: Dict[str, Dict[str, LayerSource]] = {}

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

    def _iter_matching_files(
        self, root_dir: Path, *, exclude_dirnames: Set[str] | None = None
    ):
        """Yield files under root_dir matching file_pattern without following symlinks."""
        exclude_dirnames = exclude_dirnames or set()
        for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=False):
            dirpath_path = Path(dirpath)
            # Prune excluded directories and symlinked directories.
            dirnames[:] = [
                d
                for d in dirnames
                if d not in exclude_dirnames and not (dirpath_path / d).is_symlink()
            ]
            for filename in filenames:
                if not fnmatch(filename, self.file_pattern):
                    continue
                path = dirpath_path / filename
                if path.is_symlink():
                    continue
                yield path
    
    def discover_core(self) -> Dict[str, LayerSource]:
        """Discover all core entity definitions."""
        if self._core_cache is not None:
            return self._core_cache

        entities: Dict[str, LayerSource] = {}
        type_dir = self.core_dir / self.content_type
        
        if not type_dir.exists():
            self._core_cache = entities
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
        
        self._core_cache = entities
        return entities

    # =========================================================================
    # Vendor Discovery (core < vendors < packs < overlay layers)
    # =========================================================================

    def _scan_vendor_new(self, vendor_path: Path, vendor_name: str) -> Dict[str, LayerSource]:
        """Scan vendor root for new entity definitions."""
        cached = self._vendor_new_cache.get(vendor_name)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        type_dir = vendor_path / self.content_type
        if not type_dir.exists():
            self._vendor_new_cache[vendor_name] = entities
            return entities

        for path in self._iter_matching_files(type_dir, exclude_dirnames={"overlays"}):
            if self._is_excluded(type_dir, path):
                continue
            name = self._entity_key(type_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=f"vendor:{vendor_name}",
                is_overlay=False,
                entity_name=name,
            )

        self._vendor_new_cache[vendor_name] = entities
        return entities

    def _scan_vendor_overlays(self, vendor_path: Path, vendor_name: str) -> Dict[str, LayerSource]:
        """Scan vendor root for overlay definitions."""
        cached = self._vendor_overlay_cache.get(vendor_name)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        overlays_dir = vendor_path / self.content_type / "overlays"
        if not overlays_dir.exists():
            self._vendor_overlay_cache[vendor_name] = entities
            return entities

        for path in self._iter_matching_files(overlays_dir):
            if self._is_excluded(overlays_dir, path):
                continue
            name = self._entity_key(overlays_dir, path)
            entities[name] = LayerSource(
                path=path,
                layer=f"vendor:{vendor_name}",
                is_overlay=True,
                entity_name=name,
            )

        self._vendor_overlay_cache[vendor_name] = entities
        return entities

    def discover_vendor(
        self,
        existing: Optional[Set[str]] = None,
    ) -> Dict[str, LayerSource]:
        """Discover new entities from all vendor roots.

        Vendor entities that would shadow existing entities raise an error
        unless allow_shadowing is True.

        Args:
            existing: Set of already-discovered entity names (e.g., from core).
                     If None, starts with an empty set.

        Returns:
            Dict mapping entity names to LayerSource from vendor layers.
        """
        if existing is None:
            existing = set()

        result: Dict[str, LayerSource] = {}
        for vendor_name, vendor_path in self.vendor_roots:
            new_map = self._scan_vendor_new(vendor_path, vendor_name)
            for name, src in new_map.items():
                # Check shadowing against both existing and previously found vendor entities
                if (name in existing or name in result) and not self.allow_shadowing:
                    raise CompositionValidationError(
                        f"Vendor file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                        f"To extend an existing {self.content_type}, place the file in "
                        f"'{vendor_path / self.content_type}/overlays/'.\n"
                        f"To create a NEW {self.content_type}, use a unique name."
                    )
                result[name] = src
                existing.add(name)

        return result

    def discover_vendor_overlays(
        self,
        existing: Set[str],
    ) -> Dict[str, LayerSource]:
        """Discover overlays from all vendor roots.

        Overlays must reference entities that exist in lower-precedence layers.

        Args:
            existing: Set of known entity names from core + earlier vendors.

        Returns:
            Dict mapping entity names to LayerSource (overlays only).
        """
        result: Dict[str, LayerSource] = {}
        for vendor_name, vendor_path in self.vendor_roots:
            over_map = self._scan_vendor_overlays(vendor_path, vendor_name)
            for name, src in over_map.items():
                if name not in existing:
                    raise CompositionValidationError(
                        f"Vendor overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                        f"Available {self.content_type}: {sorted(existing)}\n"
                        f"To create a NEW {self.content_type}, place the file in "
                        f"'{vendor_path / self.content_type}/' (not overlays/)."
                    )
                result[name] = src

        return result

    def iter_vendor_layers(
        self,
        existing: Set[str],
    ) -> List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]]:
        """Discover vendor new+overlay sources across all vendor roots in order.

        Mutates ``existing`` to include newly discovered vendor-defined entities
        so later vendors and overlays can reference them.

        Returns:
            List of (vendor_name, new_entities, overlay_entities) tuples.
        """
        results: List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]] = []

        for vendor_name, vendor_path in self.vendor_roots:
            new_map = self._scan_vendor_new(vendor_path, vendor_name)
            # Validate: vendor new must NOT shadow existing.
            for name, src in new_map.items():
                if name in existing and not self.allow_shadowing:
                    raise CompositionValidationError(
                        f"Vendor file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                        f"To extend an existing {self.content_type}, place the file in "
                        f"'{vendor_path / self.content_type}/overlays/'.\n"
                        f"To create a NEW {self.content_type}, use a unique name."
                    )
            existing.update(new_map.keys())

            over_map = self._scan_vendor_overlays(vendor_path, vendor_name)
            # Validate: overlays must reference existing entities.
            for name, src in over_map.items():
                if name not in existing:
                    raise CompositionValidationError(
                        f"Vendor overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                        f"Available {self.content_type}: {sorted(existing)}\n"
                        f"To create a NEW {self.content_type}, place the file in "
                        f"'{vendor_path / self.content_type}/' (not overlays/)."
                    )

            results.append((vendor_name, new_map, over_map))

        return results

    # =========================================================================
    # Pack Discovery
    # =========================================================================

    def _scan_pack_new(self, pack_root: Path, pack: str, kind: str) -> Dict[str, LayerSource]:
        cache_key = (kind, pack)
        cached = self._pack_new_cache.get(cache_key)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        type_dir = pack_root / pack / self.content_type
        if not type_dir.exists():
            self._pack_new_cache[cache_key] = entities
            return entities

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
        return entities

    def _scan_pack_overlays(self, pack_root: Path, pack: str, kind: str) -> Dict[str, LayerSource]:
        cache_key = (kind, pack)
        cached = self._pack_overlay_cache.get(cache_key)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        overlays_dir = pack_root / pack / self.content_type / "overlays"
        if not overlays_dir.exists():
            self._pack_overlay_cache[cache_key] = entities
            return entities

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
        return entities

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
                if name in existing and not self.allow_shadowing:
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
        cached = self._layer_new_cache.get(cache_key)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        type_dir = base / self.content_type
        if not type_dir.exists():
            self._layer_new_cache[cache_key] = entities
            return entities

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

        self._layer_new_cache[cache_key] = entities
        return entities

    def _scan_layer_overlays(self, base: Path, *, label: str, cache_key: str) -> Dict[str, LayerSource]:
        cached = self._layer_overlay_cache.get(cache_key)
        if cached is not None:
            return cached

        entities: Dict[str, LayerSource] = {}
        overlays_dir = base / self.content_type / "overlays"
        if not overlays_dir.exists():
            self._layer_overlay_cache[cache_key] = entities
            return entities

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

        self._layer_overlay_cache[cache_key] = entities
        return entities

    def discover_layer_new(self, layer_id: str, existing: Set[str]) -> Dict[str, LayerSource]:
        """Discover new entities for an overlay layer (must NOT shadow existing)."""
        layer_path = dict(self.overlay_layers).get(layer_id)
        if layer_path is None:
            return {}
        new_map = self._scan_layer_new(layer_path, label=layer_id, cache_key=layer_id)
        for name, src in new_map.items():
            if name in existing and not self.allow_shadowing:
                raise CompositionValidationError(
                    f"Layer file '{src.path}' shadows existing {self.content_type} '{name}'.\n"
                    f"To extend an existing {self.content_type}, place the file in "
                    f"'{(layer_path / self.content_type) / 'overlays'}'.\n"
                    f"To create a NEW {self.content_type}, use a unique name."
                )
        return new_map

    def discover_layer_overlays(
        self,
        layer_id: str,
        existing: Set[str],
        *,
        lower_existing: Optional[Set[str]] = None,
    ) -> Dict[str, LayerSource]:
        """Discover overlays for an overlay layer.

        Overlays must reference existing entities.
        """
        layer_path = dict(self.overlay_layers).get(layer_id)
        if layer_path is None:
            return {}
        over_map = self._scan_layer_overlays(layer_path, label=layer_id, cache_key=layer_id)
        for name, src in over_map.items():
            if name not in existing:
                raise CompositionValidationError(
                    f"Layer overlay '{src.path}' references non-existent {self.content_type} '{name}'.\n"
                    f"Available {self.content_type}: {sorted(existing)}\n"
                    f"To create a NEW {self.content_type}, place the file in "
                    f"'{layer_path / self.content_type}/' (not overlays/)."
                )
        return over_map

    def iter_overlay_layers(
        self,
        existing: Set[str],
    ) -> List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]]:
        """Iterate overlay layers in precedence order (new then overlays)."""
        results: List[Tuple[str, Dict[str, LayerSource], Dict[str, LayerSource]]] = []
        for layer_id, _layer_path in self.overlay_layers:
            new_map = self.discover_layer_new(layer_id, existing)
            existing.update(new_map.keys())
            over_map = self.discover_layer_overlays(layer_id, existing)
            results.append((layer_id, new_map, over_map))
        return results

    # Backward-compatible helpers for legacy callers
    def discover_user_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        return self.discover_layer_new("user", existing)

    def discover_user_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        return self.discover_layer_overlays("user", existing)

    def discover_project_new(self, existing: Set[str]) -> Dict[str, LayerSource]:
        return self.discover_layer_new("project", existing)

    def discover_project_overlays(self, existing: Set[str]) -> Dict[str, LayerSource]:
        return self.discover_layer_overlays("project", existing)
