"""Centralized session configuration accessor.

This module provides a single point of access for SessionConfig,
using lru_cache to ensure consistent configuration across the codebase.

Usage:
    from edison.core.session._config import get_config
    
    config = get_config()
    states = config.get_session_states()
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.config.domains import SessionConfig


@lru_cache(maxsize=16)
def _get_config_for_root(resolved_root: Path) -> "SessionConfig":
    """Return SessionConfig cached by resolved repo root."""
    from edison.core.config.domains import SessionConfig

    return SessionConfig(repo_root=resolved_root)


def get_config(repo_root: Optional[Path] = None) -> "SessionConfig":
    """Get the cached SessionConfig instance for the active project.

    IMPORTANT: Callers typically omit `repo_root`. In that case we *must* cache
    by the resolved project root path (not by `None`), otherwise a long-running
    process (or a large pytest run) can accidentally reuse a SessionConfig bound
    to a different project root.
    """
    from edison.core.utils.paths import PathResolver

    resolved = Path(repo_root).resolve() if repo_root is not None else PathResolver.resolve_project_root()
    return _get_config_for_root(resolved)


def reset_config_cache() -> None:
    """Reset the cached SessionConfig.
    
    This is primarily for testing purposes to ensure clean test state
    when environment variables or config files change.
    In production, this should rarely be needed.
    """
    _get_config_for_root.cache_clear()


# Keep session config singleton coherent with the centralized config cache.
# This ensures `edison.core.config.cache.clear_all_caches()` is sufficient.
from edison.core.config.cache import register_cache_clearer

register_cache_clearer("session._config.get_config", reset_config_cache)


__all__ = ["get_config", "reset_config_cache"]




