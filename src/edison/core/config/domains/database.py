"""Domain-specific configuration for database settings.

Provides cached access to database configuration including connection URL,
session prefix, and adapter settings.
"""
from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig


class DatabaseConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for database settings.

    Provides typed, cached access to database configuration including:
    - Connection URL
    - Session prefix
    - Adapter settings
    - Isolation settings

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "database"

    @cached_property
    def enabled(self) -> bool:
        """Whether database is enabled."""
        return bool(self.section.get("enabled", False))

    @cached_property
    def url(self) -> str:
        """Get database URL.

        Returns:
            Database connection URL.

        Raises:
            ValueError: If URL is not configured when database is enabled.
        """
        url_raw = self.section.get("url")
        if isinstance(url_raw, str) and url_raw.strip():
            return url_raw.strip()

        raise ValueError(
            "database.url must be configured when database.enabled is true; set EDISON_database__url "
            "(preferred) or DATABASE_URL (legacy). No default is provided for security reasons."
        )

    @cached_property
    def session_prefix(self) -> str:
        """Get session database prefix.

        Returns:
            Session prefix for database naming.

        Raises:
            ValueError: If prefix is not configured or invalid.
        """
        prefix = self.section.get("sessionPrefix")
        if not prefix:
            raise ValueError(
                "Missing configuration: database.sessionPrefix in project config (config.yml or defaults)."
            )
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(prefix)):
            raise ValueError(
                "Invalid database.sessionPrefix: must start with a letter and contain only letters, digits, and underscores."
            )
        return str(prefix)

    @cached_property
    def adapter(self) -> Optional[str]:
        """Get database adapter name."""
        return self.section.get("adapter")

    @cached_property
    def isolation_enabled(self) -> bool:
        """Whether database isolation is enabled."""
        return bool(self.section.get("enableIsolation", False))

    def get_url_or_none(self) -> Optional[str]:
        """Get database URL or None if not configured."""
        url_raw = self.section.get("url")
        if isinstance(url_raw, str) and url_raw.strip():
            return url_raw.strip()
        return None


__all__ = ["DatabaseConfig"]




