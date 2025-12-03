"""Mixin for YAML-based registries with layered loading.

This module provides YamlLayerMixin for registries that load YAML configuration
from multiple layers (core, packs, project). Placed in composition/core/ because
it's a composition concern (loading from layers), not an entity pattern.

Used by:
- RulesRegistry
- FilePatternRegistry
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.config import ConfigManager


class YamlLayerMixin:
    """Mixin for YAML-based registries with layered loading.

    Provides reusable methods for loading YAML files and directories
    across composition layers. Classes using this mixin must have:
    - self.cfg_mgr: ConfigManager instance

    Methods:
    - _load_yaml_file: Load single YAML file
    - _load_yaml_dir: Load all YAML files from directory
    """

    cfg_mgr: ConfigManager  # Type hint for classes using this mixin

    def _load_yaml_file(
        self,
        path: Path,
        *,
        required: bool = False,
    ) -> Dict[str, Any]:
        """Load and validate YAML file using cfg_mgr.

        Args:
            path: Path to YAML file
            required: If True, raise FileNotFoundError if file doesn't exist

        Returns:
            Dictionary loaded from YAML file, or empty dict if file doesn't exist

        Raises:
            FileNotFoundError: If file doesn't exist and required=True
        """
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required YAML not found: {path}")
            return {}

        # Use cfg_mgr for consistent YAML loading
        data = self.cfg_mgr.load_yaml(path)
        return data or {}

    def _load_yaml_dir(
        self,
        dir_path: Path,
        origin: str,
    ) -> List[Dict[str, Any]]:
        """Load all YAML files from directory.

        Args:
            dir_path: Path to directory containing YAML files
            origin: Origin identifier (e.g., "core", "pack:python", "project")

        Returns:
            List of dictionaries loaded from YAML files, each with _path and _origin
            metadata added. Files are processed in sorted order.
        """
        if not dir_path.exists():
            return []

        results: List[Dict[str, Any]] = []
        for path in sorted(dir_path.glob("*.yaml")):
            data = self._load_yaml_file(path)
            data["_path"] = str(path)
            data["_origin"] = origin
            results.append(data)

        return results


__all__ = ["YamlLayerMixin"]
