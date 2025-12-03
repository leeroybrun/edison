"""Base class for sync adapters.

This module provides the abstract base class for all full-featured sync adapters
that integrate Edison composition with various IDE/client configurations.

Uses ConfigMixin for unified config loading.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths import PathResolver
from .._config import ConfigMixin


class SyncAdapter(ConfigMixin, ABC):
    """Abstract base class for all full-featured sync adapters.

    Inherits from ConfigMixin to provide unified config loading with caching.

    Sync adapters integrate Edison's composition system with specific IDE/client
    configurations. They handle:
    - Configuration loading and validation (via ConfigMixin)
    - Syncing composed outputs to client-specific formats
    - Preserving manual edits where applicable
    - Providing unified sync interfaces

    Subclasses must implement:
    - sync_all(): Execute complete synchronization workflow

    Example:
        class MyClientSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                # Sync all components
                return {"synced": [...]}
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        """Initialize the sync adapter.

        Args:
            repo_root: Project root directory. If not provided, will be resolved
                      automatically using PathResolver.
        """
        self.repo_root = Path(repo_root) if repo_root else PathResolver.resolve_project_root()
        self._cached_config: Optional[Dict[str, Any]] = None

    @abstractmethod
    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        This is the main entry point for syncing all Edison outputs to the
        target client/IDE format. The exact behavior and return structure
        depends on the specific adapter implementation.

        Returns:
            Dictionary containing sync results. Structure varies by adapter
            but typically includes lists of paths for synced files.

        Example return values:
            - ClaudeSync: {"claude_md": [Path], "agents": [Path]}
            - CursorSync: {"cursorrules": [Path], "agents": [Path], "rules": [Path]}
            - ZenSync: {"roles": {role: [Path]}, "workflows": [Path]}
        """
        pass

    @classmethod
    def create(cls, repo_root: Optional[Path] = None) -> "SyncAdapter":
        """Factory method for standard initialization.

        Args:
            repo_root: Optional project root directory.

        Returns:
            Initialized sync adapter instance.
        """
        return cls(repo_root=repo_root)


__all__ = ["SyncAdapter"]
