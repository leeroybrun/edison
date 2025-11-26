"""Shared configuration loading mixin for all adapters.

This module provides ConfigMixin, a reusable class for loading and caching
Edison configuration across all adapter implementations (Claude, Cursor, Zen, Codex).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


class ConfigMixin:
    """Mixin providing config loading with caching for adapters.

    This mixin eliminates code duplication across all adapter classes by
    providing a standardized pattern for loading and caching Edison config.

    Expected attributes (must be set by subclass):
        repo_root: Path - The repository/project root directory

    Usage:
        class MyAdapter(ConfigMixin):
            def __init__(self, repo_root: Path):
                self.repo_root = repo_root
                self._cached_config = None  # Initialize cache

            # Now you can use self.config property
    """

    # Instance attribute that will be set by each adapter instance
    _cached_config: Optional[Dict[str, Any]] = None
    repo_root: Path  # Expected to be set by subclass

    def _load_config(self) -> Dict[str, Any]:
        """Load Edison configuration with caching.

        This method:
        1. Returns cached config if available
        2. Loads config using ConfigManager with validate=False
        3. Caches the result for subsequent calls
        4. Returns empty dict on any error

        Returns:
            Dict containing Edison configuration, or empty dict on error.
        """
        if self._cached_config is not None:
            return self._cached_config

        from ..config import ConfigManager

        try:
            mgr = ConfigManager(self.repo_root)
            self._cached_config = mgr.load_config(validate=False)
        except Exception:
            # Gracefully handle missing or malformed config
            self._cached_config = {}

        return self._cached_config

    @property
    def config(self) -> Dict[str, Any]:
        """Lazy-load and return Edison configuration.

        Returns:
            Dict containing Edison configuration.
        """
        return self._load_config()


__all__ = ["ConfigMixin"]
