"""Domain-specific configuration for packs.

Provides cached access to pack-related configuration without
requiring direct ConfigManager usage throughout the codebase.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import List, Optional

from ..base import BaseDomainConfig


class PacksConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for packs.

    Provides typed, cached access to pack configuration.
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Usage:
        packs = PacksConfig(repo_root=Path("/path/to/project"))
        active = packs.active_packs  # ["react", "prisma"]
    """

    def _config_section(self) -> str:
        return "packs"

    @cached_property
    def active_packs(self) -> List[str]:
        """Get list of active packs from configuration.

        Returns:
            List of active pack names. Empty list if none configured.
        """
        active = self.section.get("active", []) or []
        return list(active)

    @cached_property
    def auto_activate(self) -> bool:
        """Whether auto-activation is enabled.

        Returns:
            True if packs should be auto-activated based on file changes.
        """
        return bool(self.section.get("autoActivate", True))

    @cached_property
    def available_packs(self) -> List[str]:
        """Get list of all available packs (discovered from packs directory).

        Returns:
            List of available pack names.
        """
        from edison.core.composition.packs import discover_packs
        packs = discover_packs(root=self._repo_root)
        return [p.name for p in packs]


__all__ = ["PacksConfig"]



