"""Centralized configuration caching.

Provides a single source of truth for loaded configuration across all domain configs.
All domain configs should use this module's caching instead of implementing their own.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import ConfigManager

# ---------------------------------------------------------------------------
# Global Cache Registry
# ---------------------------------------------------------------------------

_config_cache: Dict[str, Dict[str, Any]] = {}


def _cache_key(repo_root: Optional[Path]) -> str:
    """Generate cache key from repo_root."""
    return str(repo_root) if repo_root else "__default__"


def get_cached_config(
    repo_root: Optional[Path] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """Get configuration with caching.

    Returns the same config dict instance for the same repo_root,
    avoiding repeated file I/O.

    Args:
        repo_root: Repository root path. Uses auto-detection if None.
        validate: Whether to validate against schema.

    Returns:
        Configuration dictionary (cached).
    """
    key = _cache_key(repo_root)

    if key not in _config_cache:
        # Lazy import to avoid circular dependency
        from .manager import ConfigManager
        manager = ConfigManager(repo_root=repo_root)
        _config_cache[key] = manager.load_config(validate=validate)

    return _config_cache[key]


def clear_all_caches() -> None:
    """Clear all configuration caches atomically.

    Call this when configuration files have changed and need to be reloaded.
    All domain configs now use the centralized cache, so clearing _config_cache
    is sufficient.
    """
    _config_cache.clear()


def is_cached(repo_root: Optional[Path] = None) -> bool:
    """Check if config for repo_root is cached."""
    return _cache_key(repo_root) in _config_cache


__all__ = [
    "get_cached_config",
    "clear_all_caches",
    "is_cached",
]




