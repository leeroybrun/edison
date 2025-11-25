"""Path utilities for Edison core.

This package exposes the canonical path resolver used across Edison. Prefer
importing from ``lib.paths.resolver`` (or ``lib.paths``) instead of the older
``lib.pathlib`` module.
"""

from .resolver import (  # noqa: F401
    EdisonPathError,
    PathResolver,
    resolve_project_root,
    detect_session_id,
    find_evidence_round,
    is_git_repository,
    get_git_root,
)
from .project import get_project_config_dir  # noqa: F401

__all__ = [
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "detect_session_id",
    "find_evidence_round",
    "is_git_repository",
    "get_git_root",
    "get_project_config_dir",
]
