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


@lru_cache(maxsize=1)
def get_config(repo_root: Optional[Path] = None) -> "SessionConfig":
    """Get the cached SessionConfig instance.
    
    Uses lru_cache to ensure the same instance is returned across
    all calls, avoiding redundant config loading and ensuring
    consistency.
    
    Args:
        repo_root: Optional repository root path. If not provided,
                   SessionConfig will auto-detect it.
    
    Returns:
        Cached SessionConfig instance
        
    Note:
        The repo_root parameter is part of the cache key, so different
        roots will return different configs. In practice, most code
        calls this without arguments.
    """
    # Lazy import to avoid circular dependency
    from edison.core.config.domains import SessionConfig
    return SessionConfig(repo_root=repo_root)


def reset_config_cache() -> None:
    """Reset the cached SessionConfig.
    
    This is primarily for testing purposes to ensure clean test state
    when environment variables or config files change.
    In production, this should rarely be needed.
    """
    get_config.cache_clear()


__all__ = ["get_config", "reset_config_cache"]
