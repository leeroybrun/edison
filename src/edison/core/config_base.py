"""Base class for domain-specific configuration classes.

This module provides DomainConfig, an abstract base class that eliminates duplicate
initialization code across all domain-specific config classes (SessionConfig,
TaskConfig, QAConfig, OrchestratorConfig).

All domain configs share the same initialization pattern:
- Create a ConfigManager instance
- Load the full configuration
- Extract section-specific configuration
- Store repo_root for path resolution

By inheriting from DomainConfig, subclasses get all this behavior automatically,
eliminating ~12 lines of duplicate code per config class.

Example:
    >>> class SessionConfig(DomainConfig):
    ...     def __init__(self, repo_root: Optional[Path] = None):
    ...         super().__init__(repo_root=repo_root, section="session")
    ...
    ...     def get_session_root_path(self) -> str:
    ...         paths = self.get_subsection("paths")
    ...         return paths.get("root", ".project/sessions")
"""
from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional

from .config import ConfigManager


class DomainConfig(ABC):
    """Abstract base class for domain-specific configuration classes.

    Provides shared initialization logic and common utilities for all domain
    configuration classes in the Edison framework.

    All domain configs need to:
    1. Initialize a ConfigManager with optional repo_root
    2. Load the full merged configuration
    3. Extract their domain-specific section
    4. Store the resolved repo_root for path operations

    This base class handles all of that, eliminating code duplication.

    Attributes:
        repo_root: Resolved repository root path
        _mgr: ConfigManager instance for loading configuration
        _full_config: Fully merged configuration (all sections)
        _section_config: Domain-specific configuration section

    Args:
        repo_root: Optional repository root. When None, ConfigManager
            auto-discovers it using PathResolver.
        section: Name of the configuration section for this domain
            (e.g., "session", "tasks", "qa", "orchestrators")
    """

    def __init__(self, repo_root: Optional[Path] = None, *, section: str) -> None:
        """Initialize domain config with optional repo_root and section name.

        Args:
            repo_root: Optional repository root for configuration resolution.
                When omitted, ConfigManager will auto-discover the project root.
            section: Configuration section name to extract from full config.
        """
        self._mgr = ConfigManager(repo_root=repo_root)
        self._full_config = self._mgr.load_config(validate=False)
        self._section_config = self._full_config.get(section, {}) or {}
        self.repo_root = self._mgr.repo_root

    def get_subsection(self, key: str) -> Dict[str, Any]:
        """Get a subsection from the domain configuration section.

        This helper safely retrieves nested configuration dictionaries,
        returning an empty dict when the key is missing or has a None value.
        This prevents KeyError and TypeError issues when accessing config.

        Args:
            key: Subsection key to retrieve (e.g., "paths", "validation")

        Returns:
            Dict containing the subsection, or empty dict if missing/None

        Example:
            >>> cfg = SessionConfig()
            >>> paths = cfg.get_subsection("paths")
            >>> root = paths.get("root", ".project/sessions")
        """
        section = self._section_config.get(key, {}) or {}
        return section if isinstance(section, dict) else {}


__all__ = ["DomainConfig"]
