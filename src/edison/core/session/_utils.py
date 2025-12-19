"""Shared utilities for session module.

This module consolidates common utility functions used across the session package.
It follows the DRY principle (#6) by extracting duplicated code into a single location.

Common patterns consolidated here:
- get_repo_dir(): Repository root resolution (from recovery.py, worktree/config_helpers.py)
- get_sessions_root(): Sessions root directory resolution (from recovery.py)
- get_session_config(): Session configuration accessor (helper wrapper)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.paths import PathResolver
from ._config import get_config


def get_repo_dir(project_root: Optional[Path] = None) -> Path:
    """Get repository root directory.

    This is the canonical function for resolving the repository root.
    It consolidates the _get_repo_dir() implementations from:
    - recovery.py
    - worktree/config_helpers.py

    Args:
        project_root: Optional project root path. If not provided,
                     uses PathResolver to auto-detect.

    Returns:
        Resolved repository root path

    Example:
        >>> repo_dir = get_repo_dir()
        >>> print(repo_dir)
        /path/to/project
    """
    return project_root if project_root else PathResolver.resolve_project_root()


def get_sessions_root(project_root: Optional[Path] = None) -> Path:
    """Get sessions root directory.

    This is the canonical function for resolving the sessions root directory.
    It consolidates the _get_sessions_root() implementation from recovery.py.

    The sessions root is computed by:
    1. Getting the session root path from config
    2. Resolving it relative to the repository root

    Args:
        project_root: Optional project root path. If not provided,
                     uses PathResolver to auto-detect.

    Returns:
        Resolved sessions root path

    Example:
        >>> sessions_root = get_sessions_root()
        >>> print(sessions_root)
        /path/to/project/<project-management-dir>/sessions
    """
    repo_dir = get_repo_dir(project_root)
    cfg = get_config(repo_root=repo_dir)
    root_rel = cfg.get_session_root_path()
    return (repo_dir / root_rel).resolve()


def get_session_config(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Get session configuration as a dictionary.

    This is a convenience function that provides access to the raw session
    configuration dictionary. It wraps the SessionConfig object for cases
    where a simple dict is needed.

    Args:
        project_root: Optional project root path. If not provided,
                     uses PathResolver to auto-detect.

    Returns:
        Session configuration dictionary

    Example:
        >>> config = get_session_config()
        >>> states = config.get('states', {})
    """
    cfg = get_config(repo_root=project_root)
    return cfg._config


__all__ = [
    "get_repo_dir",
    "get_sessions_root",
    "get_session_config",
]
