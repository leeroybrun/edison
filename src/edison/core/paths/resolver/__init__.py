"""Centralized path resolution for Edison framework.

This module provides canonical path resolution patterns to eliminate
duplication across 50+ scripts. All path resolution MUST use these helpers
to ensure consistent behavior across tests, CLIs, and library code.

Path resolution follows these principles:
- Framework defaults come from edison.data package (bundled)
- Project config comes from .edison/config/ (project overrides)
- Generated files go to .edison/_generated/
- NO legacy .edison/core/ paths
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .base import EdisonPathError, is_git_repository, get_git_root
from .project import (
    _PROJECT_ROOT_CACHE,
    get_project_path,
    resolve_project_root,
)
from .session import _validate_session_id, detect_session_id
from .evidence import find_evidence_round, list_evidence_rounds


class PathResolver:
    """Centralized path resolution for Edison framework.

    This class provides static methods for all path resolution patterns
    used across the Edison framework. All methods are fail-fast and raise
    EdisonPathError on failures rather than returning None or invalid paths.
    """

    @staticmethod
    def resolve_project_root() -> Path:
        """Resolve project root with fail-fast validation."""
        return resolve_project_root()

    @staticmethod
    def detect_session_id(
        explicit: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """Canonical session ID detection with validation."""
        return detect_session_id(explicit=explicit, owner=owner)

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        """Validate session ID format."""
        return _validate_session_id(session_id)

    @staticmethod
    def find_evidence_round(
        task_id: str,
        round: Optional[int] = None,
    ) -> Path:
        """Evidence directory resolution with round detection."""
        return find_evidence_round(task_id, round=round)

    @staticmethod
    def list_evidence_rounds(task_id: str) -> List[Path]:
        """List all evidence round directories for a task."""
        return list_evidence_rounds(task_id)

    @staticmethod
    def get_project_path(*parts: str) -> Path:
        """Get path relative to project root: .project/{parts}."""
        return get_project_path(*parts)


__all__ = [
    "EdisonPathError",
    "PathResolver",
    "resolve_project_root",
    "detect_session_id",
    "find_evidence_round",
    "is_git_repository",
    "get_git_root",
    "_PROJECT_ROOT_CACHE",
]
