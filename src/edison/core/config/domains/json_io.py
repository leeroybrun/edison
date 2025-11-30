"""Domain-specific configuration for JSON I/O operations.

Provides cached access to JSON I/O configuration including formatting
and encoding settings used by atomic write operations.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig


class JSONIOConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for JSON I/O operations.

    Provides typed, cached access to JSON I/O configuration including:
    - Indentation level
    - Key sorting behavior
    - ASCII encoding mode
    - Character encoding

    Note: Lock timeout settings are in TimeoutsConfig.

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "json_io"

    @cached_property
    def indent(self) -> int:
        """Get JSON indentation level."""
        return int(self.section["indent"])

    @cached_property
    def sort_keys(self) -> bool:
        """Get whether to sort JSON object keys."""
        return bool(self.section["sort_keys"])

    @cached_property
    def ensure_ascii(self) -> bool:
        """Get whether to escape non-ASCII characters."""
        return bool(self.section["ensure_ascii"])

    @cached_property
    def encoding(self) -> str:
        """Get file encoding for JSON I/O."""
        return str(self.section["encoding"])

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all JSON I/O settings as a dict.

        Returns:
            Dict with indent, sort_keys, ensure_ascii, encoding.
        """
        return {
            "indent": self.indent,
            "sort_keys": self.sort_keys,
            "ensure_ascii": self.ensure_ascii,
            "encoding": self.encoding,
        }


__all__ = [
    "JSONIOConfig",
]
