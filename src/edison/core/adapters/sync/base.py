"""Base class for sync adapters.

This module provides the abstract base class for all full-featured sync adapters
that integrate Edison composition with various IDE/client configurations.

Following SOLID principles:
- Single Responsibility: Base class only defines the contract
- Open/Closed: Open for extension via subclassing, closed for modification
- Liskov Substitution: All sync adapters can be used interchangeably
- Interface Segregation: Minimal interface with only essential methods
- Dependency Inversion: Depends on abstractions (ABC) not concrete implementations

Following DRY principle:
- Extracts common initialization and config loading patterns
- Provides reusable factory method
- Centralizes root path resolution logic
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths import PathResolver


class SyncAdapter(ABC):
    """Abstract base class for all full-featured sync adapters.

    Sync adapters integrate Edison's composition system with specific IDE/client
    configurations. They handle:
    - Configuration loading and validation
    - Syncing composed outputs to client-specific formats
    - Preserving manual edits where applicable
    - Providing unified sync interfaces

    Subclasses must implement:
    - _load_config(): Load adapter-specific configuration
    - sync_all(): Execute complete synchronization workflow

    Example:
        class MyClientSync(SyncAdapter):
            def _load_config(self) -> Dict[str, Any]:
                # Load client-specific config
                return {...}

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
        self._config = self._load_config()

    @abstractmethod
    def _load_config(self) -> Dict[str, Any]:
        """Load adapter-specific configuration.

        Subclasses override this to provide their specific configuration loading
        logic. This may include:
        - Loading from YAML config files
        - Reading environment variables
        - Setting up registries and managers
        - Validating configuration structure

        Returns:
            Configuration dictionary for this adapter.

        Raises:
            Various exceptions depending on config loading requirements.
        """
        pass

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

        Provides a convenient way to instantiate sync adapters with
        consistent initialization patterns.

        Args:
            repo_root: Optional project root directory.

        Returns:
            Initialized sync adapter instance.

        Example:
            adapter = ClaudeSync.create()
            # or
            adapter = ClaudeSync.create(repo_root=Path("/custom/path"))
        """
        return cls(repo_root=repo_root)


__all__ = ["SyncAdapter"]
