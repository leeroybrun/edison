"""Domain-specific configuration for Context7 package detection.

Provides cached access to Context7-related configuration including
triggers, aliases, and package metadata.
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
        # Load from bundled defaults
        from edison.data import read_yaml
        try:
            cfg = read_yaml("config", "context7.yml")
            triggers = cfg.get("triggers", {})
            if isinstance(triggers, dict):
                # Ensure all values are lists
                return {k: list(v) if isinstance(v, list) else [] for k, v in triggers.items()}
        except Exception:
            pass
        return {}

    @cached_property
    def aliases(self) -> Dict[str, str]:
        """Return package name aliases for normalization.

        Returns:
            Dict mapping alias names to canonical package names.
            Empty dict if not configured.
        """
        # Load from bundled defaults
        from edison.data import read_yaml
        try:
            cfg = read_yaml("config", "context7.yml")
            aliases = cfg.get("aliases", {})
            if isinstance(aliases, dict):
                return {k: str(v) for k, v in aliases.items()}
        except Exception:
            pass
        return {}

    @cached_property
    def packages(self) -> Dict[str, Any]:
        """Return package metadata (version, context7Id, etc).

        Returns:
            Dict mapping package names to their metadata.
            Empty dict if not configured.
        """
        # Load from bundled defaults
        from edison.data import read_yaml
        try:
            cfg = read_yaml("config", "context7.yml")
            packages = cfg.get("packages", {})
            if isinstance(packages, dict):
                return packages
        except Exception:
            pass
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
        # Load from bundled defaults
        from edison.data import read_yaml
        try:
            cfg = read_yaml("config", "context7.yml")
            detection = cfg.get("contentDetection", {})
            if isinstance(detection, dict):
                return detection
        except Exception:
            pass
        return {}

    def get_content_detection(self) -> Dict[str, Dict[str, List[str]]]:
        """Return content detection patterns for packages."""
        return self.content_detection


__all__ = [
    "Context7Config",
]
