"""Config-driven adapter loader.

Dynamically loads and executes adapters from composition.yaml.
NO hardcoded adapter lists - everything is config-driven.

Usage:
    loader = AdapterLoader(project_root)
    
    # Get enabled adapters
    for name in loader.get_enabled_adapter_names():
        adapter = loader.load_adapter(name)
        adapter.sync_all()
    
    # Or run all at once
    results = loader.run_all_adapters()
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from edison.core.config.domains.composition import (
    CompositionConfig,
    AdapterConfig,
)

if TYPE_CHECKING:
    from .base import PlatformAdapter


class AdapterLoader:
    """Dynamically loads and executes adapters from config.
    
    This loader uses CompositionConfig to discover available adapters
    and dynamically imports their classes. No adapters are hardcoded.
    
    Usage:
        loader = AdapterLoader(project_root)
        
        # List available adapters
        print(loader.get_enabled_adapter_names())  # ['claude', 'cursor', 'pal', ...]
        
        # Load a specific adapter
        adapter = loader.load_adapter('claude')
        results = adapter.sync_all()
        
        # Or run all at once
        all_results = loader.run_all_adapters()
    """
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize the adapter loader.
        
        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        from edison.core.utils.paths import PathResolver
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._comp_config = CompositionConfig(repo_root=self.project_root)
        self._adapters_cache: Dict[str, "PlatformAdapter"] = {}
    
    # =========================================================================
    # Adapter Discovery
    # =========================================================================
    
    def get_enabled_adapter_names(self) -> List[str]:
        """Return names of enabled adapters."""
        return [a.name for a in self._comp_config.get_enabled_adapters()]
    
    def get_all_adapter_names(self) -> List[str]:
        """Return names of all adapters (enabled and disabled)."""
        return list(self._comp_config.adapters.keys())
    
    def get_adapter_config(self, name: str) -> Optional[AdapterConfig]:
        """Get configuration for a specific adapter."""
        return self._comp_config.get_adapter(name)
    
    def is_adapter_enabled(self, name: str) -> bool:
        """Check if an adapter is enabled."""
        return self._comp_config.is_adapter_enabled(name)
    
    # =========================================================================
    # Adapter Loading
    # =========================================================================
    
    def load_adapter(self, name: str) -> Optional["PlatformAdapter"]:
        """Load an adapter by name.
        
        Dynamically imports the adapter class from the config.
        Caches loaded adapters for reuse.
        
        Args:
            name: Adapter name (e.g., "claude", "cursor", "pal")
            
        Returns:
            PlatformAdapter instance or None if not found
        """
        if name in self._adapters_cache:
            return self._adapters_cache[name]
        
        adapter_cfg = self._comp_config.get_adapter(name)
        if not adapter_cfg:
            return None
        
        # Dynamic import
        class_path = adapter_cfg.adapter_class
        if not class_path:
            return None
        
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            adapter_class: Type["PlatformAdapter"] = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            # Log error but don't crash
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to load adapter '{name}' from '{class_path}': {e}"
            )
            return None
        
        # Instantiate with config
        adapter = adapter_class(
            project_root=self.project_root,
            adapter_config=adapter_cfg,
        )
        
        self._adapters_cache[name] = adapter
        return adapter
    
    def clear_cache(self) -> None:
        """Clear the adapter cache."""
        self._adapters_cache.clear()
    
    # =========================================================================
    # Adapter Execution
    # =========================================================================
    
    def run_adapter(self, name: str) -> Dict[str, Any]:
        """Run a specific adapter and return results.
        
        Args:
            name: Adapter name
            
        Returns:
            Dict with sync results or error information
        """
        adapter = self.load_adapter(name)
        if not adapter:
            return {"error": f"Adapter '{name}' not found or failed to load"}
        
        try:
            return adapter.sync_all()
        except Exception as e:
            return {"error": str(e)}
    
    def run_enabled_adapters(self) -> Dict[str, Dict[str, Any]]:
        """Run all enabled adapters and return results.
        
        Returns:
            Dict mapping adapter names to their sync results
        """
        results: Dict[str, Dict[str, Any]] = {}
        for name in self.get_enabled_adapter_names():
            results[name] = self.run_adapter(name)
        return results
    
    def run_adapters(self, names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Run specific adapters by name.
        
        Args:
            names: List of adapter names to run
            
        Returns:
            Dict mapping adapter names to their sync results
        """
        results: Dict[str, Dict[str, Any]] = {}
        for name in names:
            results[name] = self.run_adapter(name)
        return results


__all__ = ["AdapterLoader"]

