"""Path utilities for Edison.

This package provides centralized path resolution:
- Resolver: project root resolution, PathResolver class
- Management: project management paths (.project/*)
- Project: project config directory detection
- Evidence: QA evidence path resolution
"""
from __future__ import annotations

from .evidence import (
    find_evidence_round,
    list_evidence_rounds,
)
from .management import (
    ProjectManagementPaths,
    get_management_paths,
)
from .project import (
    DEFAULT_PROJECT_CONFIG_PRIMARY,
    get_project_config_dir,
)
from .user import (
    DEFAULT_USER_CONFIG_PRIMARY,
    get_user_config_dir,
)
from .resolver import (
    EdisonPathError,
    PathResolver,
    _PROJECT_ROOT_CACHE,
    get_project_path,
    resolve_project_root,
)

__all__ = [
    # resolver
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "get_project_path",
    "_PROJECT_ROOT_CACHE",
    # management
    "ProjectManagementPaths",
    "get_management_paths",
    # project
    "DEFAULT_PROJECT_CONFIG_PRIMARY",
    "get_project_config_dir",
    # user
    "DEFAULT_USER_CONFIG_PRIMARY",
    "get_user_config_dir",
    # evidence
    "find_evidence_round",
    "list_evidence_rounds",
]



