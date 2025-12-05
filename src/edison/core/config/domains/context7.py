"""Domain-specific configuration for Context7 package detection.

Provides cached access to Context7-related configuration including
triggers, aliases, and package metadata.

Configuration is loaded from bundled edison.data/config/context7.yaml
with project overrides from .edison/config/context7.yaml merged on top.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseDomainConfig


class Context7Config(BaseDomainConfig):
    """Context7 configuration access following the DomainConfig pattern.

    Provides structured access to Context7-related configuration with repo_root exposure.
    Extends BaseDomainConfig for consistent caching and repo_root handling.
    
    Configuration layering:
    1. Bundled defaults from edison.data/config/context7.yaml
    2. Project overrides from .edison/config/context7.yaml merged on top
    """

    def _config_section(self) -> str:
        return "context7"

    @cached_property
    def triggers(self) -> Dict[str, List[str]]:
        """Return file pattern triggers for package detection.

        Returns:
            Dict mapping package names to lists of file patterns.
            Empty dict if not configured.
        """
        triggers = self.section.get("triggers", {})
        if isinstance(triggers, dict):
            # Ensure all values are lists
            return {k: list(v) if isinstance(v, list) else [] for k, v in triggers.items()}
        return {}

    @cached_property
    def aliases(self) -> Dict[str, str]:
        """Return package name aliases for normalization.

        Returns:
            Dict mapping alias names to canonical package names.
            Empty dict if not configured.
        """
        aliases = self.section.get("aliases", {})
        if isinstance(aliases, dict):
            return {k: str(v) for k, v in aliases.items()}
        return {}

    @cached_property
    def packages(self) -> Dict[str, Any]:
        """Return package metadata (version, context7Id, etc).

        Returns:
            Dict mapping package names to their metadata.
            Empty dict if not configured.
        """
        packages = self.section.get("packages", {})
        if isinstance(packages, dict):
            return packages
        return {}

    def get_triggers(self) -> Dict[str, List[str]]:
        """Return file pattern triggers for package detection."""
        return self.triggers

    def get_aliases(self) -> Dict[str, str]:
        """Return package name aliases for normalization."""
        return self.aliases

    def get_packages(self) -> Dict[str, Any]:
        """Return package metadata."""
        return self.packages

    @cached_property
    def content_detection(self) -> Dict[str, Dict[str, List[str]]]:
        """Return content detection patterns for packages.

        Returns:
            Dict mapping package names to detection config with:
            - filePatterns: List of glob patterns for files to search
            - searchPatterns: List of regex patterns to search for in content
            Empty dict if not configured.
        """
        detection = self.section.get("contentDetection", {})
        if isinstance(detection, dict):
            return detection
        return {}

    def get_content_detection(self) -> Dict[str, Dict[str, List[str]]]:
        """Return content detection patterns for packages."""
        return self.content_detection


__all__ = [
    "Context7Config",
]
