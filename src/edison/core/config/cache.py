"""Centralized configuration caching.

Provides a single source of truth for loaded configuration across all domain configs.
All domain configs should use this module's caching instead of implementing their own.

The cache supports pack-aware configuration loading. By default, pack configs are
included in the cached configuration (include_packs=True).
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


def _cache_key(repo_root: Optional[Path], include_packs: bool = True) -> str:
    """Generate cache key from repo_root and include_packs flag.

    Args:
        repo_root: Repository root path
        include_packs: Whether pack configs are included

    Returns:
        Cache key string
    """
    base = str(repo_root) if repo_root else "__default__"
    suffix = ":packs" if include_packs else ":no_packs"
    return base + suffix


def get_cached_config(
    repo_root: Optional[Path] = None,
    validate: bool = False,
    include_packs: bool = True,
) -> Dict[str, Any]:
    """Get configuration with caching.

    Returns the same config dict instance for the same repo_root and include_packs,
    avoiding repeated file I/O.

    Args:
        repo_root: Repository root path. Uses auto-detection if None.
        validate: Whether to validate against schema.
        include_packs: Whether to include pack config overlays (default: True).

    Returns:
        Configuration dictionary (cached).
    """
    key = _cache_key(repo_root, include_packs)

    if key not in _config_cache:
        # Lazy import to avoid circular dependency
        from .manager import ConfigManager

        manager = ConfigManager(repo_root=repo_root)
        _config_cache[key] = manager.load_config(
            validate=validate, include_packs=include_packs
        )

    return _config_cache[key]


def clear_all_caches() -> None:
    """Clear all configuration caches atomically.

    Call this when configuration files have changed and need to be reloaded.
    All domain configs now use the centralized cache, so clearing _config_cache
    is sufficient.
    """
    _config_cache.clear()


def is_cached(repo_root: Optional[Path] = None, include_packs: bool = True) -> bool:
    """Check if config for repo_root is cached.

    Args:
        repo_root: Repository root path
        include_packs: Whether pack configs are included

    Returns:
        True if configuration is cached
    """
    return _cache_key(repo_root, include_packs) in _config_cache


__all__ = [
    "get_cached_config",
    "clear_all_caches",
    "is_cached",
]




