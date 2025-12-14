"""Base class for domain-specific configuration accessors.

Provides a standardized pattern for all domain configs with:
- Centralized caching via cache.py
- Consistent repo_root handling
- Type-safe section access
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from .cache import get_cached_config


class BaseDomainConfig(ABC):
    """Abstract base class for domain-specific configuration accessors.

    All domain configs (PacksConfig, SessionConfig, QAConfig, etc.) should
    extend this class to ensure consistent behavior:
    - Centralized caching
    - Standardized repo_root handling
    - Type-safe config section access

    Usage:
        class MyConfig(BaseDomainConfig):
            def _config_section(self) -> str:
                return "mySection"

            @cached_property
            def my_setting(self) -> str:
                return self.section.get("mySetting", "default")

        cfg = MyConfig(repo_root=Path("/path/to/project"))
        print(cfg.my_setting)
    """

    def __init__(self, repo_root: Optional[Path] = None, *, include_packs: bool = True) -> None:
        """Initialize domain config.

        Args:
            repo_root: Repository root path. Uses auto-detection if None.
            include_packs: Whether to include pack config overlays (default: True).
        """
        self._repo_root = repo_root
        # Load config via centralized cache
        self._config = get_cached_config(repo_root=repo_root, include_packs=include_packs)

    @property
    def repo_root(self) -> Path:
        """Get the repository root path.

        Returns the explicitly provided repo_root, or resolves it if not provided.
        """
        if self._repo_root:
            return self._repo_root

        # Resolve if not explicitly provided
        from edison.core.utils.paths import PathResolver
        return PathResolver.resolve_project_root()

    @abstractmethod
    def _config_section(self) -> str:
        """Return the top-level config key for this domain.

        Subclasses must implement this to specify which section of the
        config they represent (e.g., 'packs', 'session', 'orchestrators').

        Returns:
            The top-level key in the configuration dict.
        """
        ...

    @cached_property
    def section(self) -> Dict[str, Any]:
        """Get this domain's configuration section.

        Returns:
            The config section dict, or empty dict if section doesn't exist.
        """
        return self._config.get(self._config_section(), {}) or {}


__all__ = ["BaseDomainConfig"]




