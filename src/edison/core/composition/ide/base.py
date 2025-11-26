#!/usr/bin/env python3
from __future__ import annotations

"""Base class for IDE configuration composers."""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import ConfigManager
from ...config.domains import PacksConfig
from ...utils.paths.project import get_project_config_dir
from ...utils.paths import PathResolver


class IDEComposerBase(ABC):
    """Base class providing shared initialization and utilities for IDE composers.
    
    Subclasses: HookComposer, CommandComposer, SettingsComposer
    
    Provides:
    - Standardized repo_root and config loading
    - Shared path resolution (core_dir, packs_dir, project_dir)
    - Canonical active_packs via PacksConfig
    - Common YAML/file loading patterns
    """

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        """Initialize composer with config and repo root.
        
        Args:
            config: Optional config dict to merge with loaded config.
            repo_root: Repository root path. Resolved automatically if not provided.
        """
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.cfg_mgr = ConfigManager(self.repo_root)
        
        base_cfg = self.cfg_mgr.load_config(validate=False)
        self.config = self.cfg_mgr.deep_merge(base_cfg, config or {})
        
        # Standard directory layout
        config_dir = get_project_config_dir(self.repo_root, create=False)
        self.core_dir = config_dir / "core"
        self.packs_dir = config_dir / "packs"
        self.project_dir = config_dir

    @property
    def _packs_config(self) -> PacksConfig:
        """Lazy PacksConfig accessor."""
        return PacksConfig(repo_root=self.repo_root)

    def _active_packs(self) -> List[str]:
        """Get active packs via PacksConfig."""
        return self._packs_config.active_packs

    def _load_yaml_safe(self, path: Path) -> Dict[str, Any]:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        return self.cfg_mgr.load_yaml(path) or {}

    def _merge_from_file(
        self, base: Dict[str, Any], path: Path, key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Merge YAML file contents into base dict.
        
        Args:
            base: Base dictionary to merge into.
            path: Path to YAML file.
            key: Optional key to extract from loaded YAML before merging.
            
        Returns:
            Merged dictionary.
        """
        data = self._load_yaml_safe(path)
        if key:
            data = data.get(key, {}) or {}
        if not data:
            return base
        return self.cfg_mgr.deep_merge(base, data)


__all__ = ["IDEComposerBase"]
