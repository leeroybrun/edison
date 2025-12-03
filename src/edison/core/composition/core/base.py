"""Base class for composition infrastructure.

Provides common initialization and path setup for:
- BaseRegistry classes (agents, validators, guidelines)
- IDE composers (hooks, commands, settings)
- Any composition-related component

Consolidates duplicate code from various registries and composers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from edison.core.config import ConfigManager
from edison.core.config.domains import PacksConfig
from edison.core.utils.paths.project import get_project_config_dir
from edison.core.utils.paths import PathResolver
from edison.data import get_data_path


class CompositionBase(ABC):
    """Shared base for registries and IDE composers.

    Provides:
    - Unified path resolution (project_root, project_dir)
    - Config manager access (self.cfg_mgr, self.config)
    - Active packs discovery (get_active_packs())
    - YAML loading utilities (load_yaml_safe, merge_yaml)
    - Definition merging (merge_definitions)

    Subclasses MUST implement _setup_composition_dirs() to set:
    - self.core_dir
    - self.bundled_packs_dir
    - self.project_packs_dir
    """

    # Declare attributes for type checking
    core_dir: Path
    bundled_packs_dir: Path
    project_packs_dir: Path

    def __init__(
        self,
        project_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize base composition infrastructure.

        Args:
            project_root: Repository root path. Resolved automatically if not provided.
            config: Optional config dict to merge with loaded config.
        """
        # Path resolution - UNIFIED
        self.project_root = project_root or PathResolver.resolve_project_root()
        self.project_dir = get_project_config_dir(self.project_root, create=False)

        # Config - UNIFIED
        self.cfg_mgr = ConfigManager(self.project_root)
        base_cfg = self.cfg_mgr.load_config(validate=False)
        self.config = self.cfg_mgr.deep_merge(base_cfg, config or {})

        # Active packs - UNIFIED (lazy via property)
        self._packs_config_cache: Optional[PacksConfig] = None

        # Lazy writer - UNIFIED
        self._writer: Optional["CompositionFileWriter"] = None  # type: ignore[name-defined]

        # Subclass-specific paths
        self._setup_composition_dirs()

    # =========================================================================
    # Writer Property
    # =========================================================================

    @property
    def writer(self) -> "CompositionFileWriter":  # type: ignore[name-defined]
        """Lazy-initialized CompositionFileWriter.

        Returns:
            CompositionFileWriter instance for writing files.
        """
        if self._writer is None:
            from edison.core.composition.output.writer import CompositionFileWriter

            self._writer = CompositionFileWriter(base_dir=self.project_root)
        return self._writer

    @abstractmethod
    def _setup_composition_dirs(self) -> None:
        """Setup core/packs directories. Override in subclasses.

        Standard implementation:
            self.core_dir = Path(get_data_path(""))
            self.bundled_packs_dir = Path(get_data_path("packs"))
            self.project_packs_dir = self.project_dir / "packs"
        """
        pass

    # =========================================================================
    # Active Packs
    # =========================================================================

    @property
    def _packs_config(self) -> PacksConfig:
        """Lazy PacksConfig accessor."""
        if self._packs_config_cache is None:
            self._packs_config_cache = PacksConfig(repo_root=self.project_root)
        return self._packs_config_cache

    def get_active_packs(self) -> List[str]:
        """Get active packs list (cached)."""
        return self._packs_config.active_packs

    # =========================================================================
    # YAML Loading Utilities
    # =========================================================================

    def load_yaml_safe(self, path: Path) -> Dict[str, Any]:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def _load_yaml_with_fallback(
        self,
        primary_path: Path,
        fallback_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Load YAML with fallback path."""
        if primary_path.exists():
            return self.load_yaml_safe(primary_path)
        if fallback_path and fallback_path.exists():
            return self.load_yaml_safe(fallback_path)
        return {}

    # =========================================================================
    # Config Merging Utilities
    # =========================================================================

    def merge_yaml(
        self,
        base: Dict[str, Any],
        path: Path,
        key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge YAML file into base dict."""
        data = self.load_yaml_safe(path)
        if key:
            data = data.get(key, {}) or {}
        if not data:
            return base
        return self.cfg_mgr.deep_merge(base, data)

    def merge_definitions(
        self,
        merged: Dict[str, Dict[str, Any]],
        definitions: Any,
        key_getter: Callable[[Dict[str, Any]], Optional[str]] = lambda d: d.get("id"),
    ) -> Dict[str, Dict[str, Any]]:
        """Generic merge for definitions by unique key."""
        if isinstance(definitions, dict):
            for def_key, def_dict in definitions.items():
                if not isinstance(def_dict, dict):
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        if isinstance(definitions, list):
            for def_dict in definitions:
                if not isinstance(def_dict, dict):
                    continue
                def_key = key_getter(def_dict)
                if not def_key:
                    continue
                existing = merged.get(def_key, {})
                merged[def_key] = self.cfg_mgr.deep_merge(existing, def_dict)
            return merged

        return merged

    def _extract_definitions(
        self,
        data: Dict[str, Any],
        key: str,
    ) -> List[Dict[str, Any]]:
        """Extract definitions list from config data by key path.

        Supports nested paths using dot notation (e.g., "ide.claude.hooks").

        Args:
            data: Configuration data dictionary.
            key: Key path to extract (supports dot notation for nested keys).

        Returns:
            List of definition dicts, or empty list if not found or not a list.
        """
        # Navigate to nested key
        current = data
        for part in key.split("."):
            if not isinstance(current, dict):
                return []
            current = current.get(part)
            if current is None:
                return []

        # Return as list if it's a list, otherwise empty
        if isinstance(current, list):
            return current
        return []

    def _merge_definitions_by_id(
        self,
        base: Dict[str, Dict[str, Any]],
        new_defs: List[Dict[str, Any]],
        id_key: str = "id",
    ) -> Dict[str, Dict[str, Any]]:
        """Merge definitions list into base dict by ID.

        This is the overlay pattern: later definitions extend/override earlier ones.

        Args:
            base: Existing definitions dict (id -> definition).
            new_defs: List of new definitions to merge.
            id_key: Key to use as identifier (default: "id").

        Returns:
            Merged definitions dict.
        """
        result = dict(base)

        for def_dict in new_defs:
            if not isinstance(def_dict, dict):
                continue

            def_id = def_dict.get(id_key)
            if not def_id:
                continue

            existing = result.get(def_id, {})
            result[def_id] = self.cfg_mgr.deep_merge(existing, def_dict)

        return result

    def _load_layered_config(
        self,
        config_name: str,
        subdirs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Load config from all layers (core → packs → project).

        Searches for config_name.yaml or config_name.yml in:
        1. core_dir/{subdirs}/config_name.{yaml|yml}
        2. bundled_packs_dir/{pack}/{subdirs}/config_name.{yaml|yml} for each active pack
        3. project_packs_dir/{pack}/{subdirs}/config_name.{yaml|yml} for each active pack (if exists)
        4. project_dir/{subdirs}/config_name.{yaml|yml}

        Args:
            config_name: Name of the config file (without .yaml/.yml extension).
            subdirs: Optional subdirectory path parts.

        Returns:
            Merged configuration from all layers.
        """
        result: Dict[str, Any] = {}
        subdirs = subdirs or []

        # Helper to merge yaml with .yaml/.yml fallback
        def merge_with_ext_fallback(base: Dict[str, Any], dir_path: Path) -> Dict[str, Any]:
            yaml_path = dir_path / f"{config_name}.yaml"
            yml_path = dir_path / f"{config_name}.yml"
            if yaml_path.exists():
                return self.merge_yaml(base, yaml_path)
            if yml_path.exists():
                return self.merge_yaml(base, yml_path)
            return base

        # 1. Core layer
        result = merge_with_ext_fallback(result, self.core_dir.joinpath(*subdirs))

        # 2. Pack layers - bundled packs
        for pack in self.get_active_packs():
            pack_dir = self.bundled_packs_dir / pack / Path(*subdirs)
            result = merge_with_ext_fallback(result, pack_dir)

        # 3. Pack layers - project packs (for IDE composers, allow project-level pack overrides)
        project_packs_base = getattr(self, "project_packs_dir", None)
        if project_packs_base:
            for pack in self.get_active_packs():
                pack_dir = project_packs_base / pack / Path(*subdirs)
                result = merge_with_ext_fallback(result, pack_dir)

        # 4. Project layer
        project_subdir = self.project_dir.joinpath(*subdirs)
        result = merge_with_ext_fallback(result, project_subdir)

        return result

    def _merge_with_handlers(
        self,
        base: Dict[str, Any],
        overlay: Dict[str, Any],
        list_strategy: str = "append",
    ) -> Dict[str, Any]:
        """Merge overlay into base with configurable list handling.

        Args:
            base: Base dictionary.
            overlay: Overlay dictionary.
            list_strategy: How to handle lists - "append", "replace", or "prepend".

        Returns:
            Merged dictionary.
        """
        result = dict(base)

        for key, value in overlay.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._merge_with_handlers(
                        result[key], value, list_strategy
                    )
                elif isinstance(result[key], list) and isinstance(value, list):
                    if list_strategy == "append":
                        result[key] = result[key] + value
                    elif list_strategy == "prepend":
                        result[key] = value + result[key]
                    else:  # replace
                        result[key] = value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result
