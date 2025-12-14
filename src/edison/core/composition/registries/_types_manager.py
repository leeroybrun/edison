"""Config-driven composable types manager.

Uses CompositionConfig as the single source of truth for all content type
configuration. Provides a unified interface for discovering, composing,
and writing content types.

Usage:
    manager = ComposableTypesManager(project_root)
    
    # Get all enabled composable types
    types = manager.get_enabled_types()
    
    # Compose a specific type
    results = manager.compose_type("agents", packs)
    
    # Write composed files
    written = manager.write_type("agents", packs)
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from ..core.base import CompositionBase
from ._base import ComposableRegistry
from .generic import GenericRegistry
from edison.core.composition.includes import ComposedIncludeProvider
from edison.core.config.domains.composition import (
    CompositionConfig,
    ContentTypeConfig,
)
from edison.core.utils.profiling import span


class ComposableTypesManager(CompositionBase):
    """Manages composable content types using CompositionConfig.
    
    This is the unified interface for composing content types.
    All registry loading is config-driven - no hardcoded registry lists.
    
    Example:
        manager = ComposableTypesManager(project_root)
        
        # List all enabled types for CLI
        for type_config in manager.get_enabled_types():
            print(f"--{type_config.cli_flag}")
        
        # Compose a type
        results = manager.compose_type("cursor_rules", packs)
        
        # Write to output
        written = manager.write_type("cursor_rules", packs)
    """
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        super().__init__(project_root)
        self._comp_config = CompositionConfig(repo_root=self.project_root)
        self._registries_cache: Dict[str, ComposableRegistry] = {}
    
    # =========================================================================
    # Type Configuration Access
    # =========================================================================
    
    def get_all_types(self) -> List[ContentTypeConfig]:
        """Get all content type configurations."""
        return list(self._comp_config.content_types.values())
    
    def get_enabled_types(self) -> List[ContentTypeConfig]:
        """Get only enabled content types."""
        return self._comp_config.get_enabled_content_types()
    
    def get_type(self, name: str) -> Optional[ContentTypeConfig]:
        """Get a specific content type by name."""
        return self._comp_config.get_content_type(name)
    
    def get_type_by_cli_flag(self, flag: str) -> Optional[ContentTypeConfig]:
        """Get content type by CLI flag name."""
        return self._comp_config.get_content_type_by_cli_flag(flag)
    
    # =========================================================================
    # Registry Access
    # =========================================================================
    
    def get_registry(self, type_name: str) -> Optional[ComposableRegistry]:
        """Get or create a registry for a content type.
        
        Dynamically loads registry class from config. Falls back to
        GenericRegistry if no specific registry is configured.
        
        Args:
            type_name: The content type name (e.g., "agents", "cursor_rules")
            
        Returns:
            Registry instance or None if type not found
        """
        if type_name in self._registries_cache:
            return self._registries_cache[type_name]
        
        type_cfg = self.get_type(type_name)
        if not type_cfg:
            return None
        
        # Load registry class dynamically
        if type_cfg.registry:
            registry = self._load_registry_class(type_cfg.registry, type_cfg)
        else:
            # Use GenericRegistry
            registry = GenericRegistry(
                content_type=type_cfg.content_path,
                file_pattern=type_cfg.file_pattern,
                project_root=self.project_root,
            )
        
        self._registries_cache[type_name] = registry
        return registry
    
    def _load_registry_class(
        self,
        class_path: str,
        type_cfg: ContentTypeConfig,
    ) -> ComposableRegistry:
        """Dynamically load a registry class from module path.
        
        Args:
            class_path: Full module path to registry class
                       (e.g., "edison.core.composition.registries.agents.AgentRegistry")
            type_cfg: Content type configuration
            
        Returns:
            Instantiated registry
        """
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        registry_class: Type[ComposableRegistry] = getattr(module, class_name)
        return registry_class(project_root=self.project_root)
    
    # =========================================================================
    # Composition
    # =========================================================================
    
    def compose_type(
        self,
        type_name: str,
        packs: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Compose all entities of a type.
        
        Args:
            type_name: The content type name
            packs: Active packs (uses config if not specified)
            
        Returns:
            Dict mapping entity names to composed content (as strings)
        """
        with span("compose.type.compose", type=type_name):
            registry = self.get_registry(type_name)
            if not registry:
                return {}
            
            packs = packs or registry.get_active_packs()
            include_provider = ComposedIncludeProvider(
                types_manager=self,
                packs=tuple(packs),
                materialize=False,
            ).build()
            results = registry.compose_all(packs, include_provider=include_provider)
            
            # Normalize to strings (handle custom result types)
            return {name: self._to_string(result) for name, result in results.items()}
    
    def _to_string(self, result: Any) -> str:
        """Convert registry result to string.
        
        Handles different result types from specialized registries.
        """
        if isinstance(result, str):
            return result
        return str(result)
    
    # =========================================================================
    # Writing
    # =========================================================================
    
    def write_type(
        self,
        type_name: str,
        packs: Optional[List[str]] = None,
        path_mapper: Optional[Callable[[Path], Path]] = None,
    ) -> List[Path]:
        """Compose and write all entities of a type.
        
        Args:
            type_name: The content type name
            packs: Active packs (uses config if not specified)
            
        Returns:
            List of written file paths
        """
        with span("compose.type.write", type=type_name):
            type_cfg = self.get_type(type_name)
            if not type_cfg or not type_cfg.enabled:
                return []

            registry = self.get_registry(type_name)
            if not registry:
                return []

            packs = packs or registry.get_active_packs()
            include_provider = ComposedIncludeProvider(
                types_manager=self,
                packs=tuple(packs),
                materialize=True,
                path_mapper=path_mapper,
            ).build()

            composed = registry.compose_all(packs, include_provider=include_provider)
            results = {name: self._to_string(obj) for name, obj in composed.items()}
            if not results:
                return []
            
            output_path = self._comp_config.resolve_output_path(type_cfg.output_path)
            
            written: List[Path] = []
            for name, content in results.items():
                with span("compose.file.write", type=type_name, entity=name):
                    file_path = self._resolve_file_path(type_cfg, name, output_path)
                    target_path = path_mapper(file_path) if path_mapper else file_path
                    # Unified output writer (single source of truth for file writes)
                    self.writer.write_text(target_path, content)
                    written.append(target_path)

            # Prune stale generated files for this type.
            # IMPORTANT: We only prune inside the project's `_generated/` subtree and
            # never the `_generated/` root itself (it contains multiple types).
            try:
                from edison.core.utils.paths import get_project_config_dir

                project_dir = get_project_config_dir(self.project_root, create=False)
                generated_root = (project_dir / "_generated").resolve()
                out_dir = output_path.resolve()
                if out_dir != generated_root and generated_root in out_dir.parents:
                    written_set = {p.resolve() for p in written}
                    # Remove any files under output_path that were not written this run.
                    for p in out_dir.rglob("*"):
                        try:
                            if p.is_file() and p.resolve() not in written_set:
                                p.unlink()
                        except Exception:
                            continue
                    # Clean up empty directories (deepest first).
                    for p in sorted(out_dir.rglob("*"), key=lambda x: len(x.as_posix()), reverse=True):
                        try:
                            if p.is_dir() and not any(p.iterdir()):
                                p.rmdir()
                        except Exception:
                            continue
            except Exception:
                # Never fail composition due to cleanup.
                pass
            
            return written
    
    def _resolve_file_path(
        self,
        type_cfg: ContentTypeConfig,
        name: str,
        output_path: Path,
    ) -> Path:
        """Resolve the output file path for an entity.
        
        Handles output_mapping overrides for specific files.
        """
        # Check for output_mapping override
        if name in type_cfg.output_mapping:
            return self.project_root / type_cfg.output_mapping[name]
        
        # Use filename pattern
        filename = type_cfg.filename_pattern.format(name=name, NAME=name.upper())
        return output_path / filename
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    
    def compose_all(
        self,
        packs: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """Compose all enabled content types.
        
        Args:
            packs: Active packs (uses config if not specified)
            
        Returns:
            Dict mapping type names to their composed entities
        """
        results: Dict[str, Dict[str, str]] = {}
        for type_cfg in self.get_enabled_types():
            results[type_cfg.name] = self.compose_type(type_cfg.name, packs)
        return results
    
    def write_all(
        self,
        packs: Optional[List[str]] = None,
    ) -> Dict[str, List[Path]]:
        """Compose and write all enabled content types.
        
        Args:
            packs: Active packs (uses config if not specified)
            
        Returns:
            Dict mapping type names to lists of written file paths
        """
        results: Dict[str, List[Path]] = {}
        for type_cfg in self.get_enabled_types():
            results[type_cfg.name] = self.write_type(type_cfg.name, packs)
        return results


__all__ = [
    "ComposableTypesManager",
]
