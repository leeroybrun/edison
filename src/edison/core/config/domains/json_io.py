"""Domain-specific configuration for JSON I/O operations.

Provides cached access to JSON I/O configuration including formatting
and encoding settings used by atomic write operations.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig

# Default configuration values
DEFAULT_INDENT = 2
DEFAULT_SORT_KEYS = True
DEFAULT_ENSURE_ASCII = False
DEFAULT_ENCODING = "utf-8"


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
        """Get JSON indentation level (default: 2)."""
        indent_val = self.section.get("indent", DEFAULT_INDENT)
        return int(indent_val)

    @cached_property
    def sort_keys(self) -> bool:
        """Get whether to sort JSON object keys (default: True)."""
        sort = self.section.get("sort_keys", DEFAULT_SORT_KEYS)
        return bool(sort)

    @cached_property
    def ensure_ascii(self) -> bool:
        """Get whether to escape non-ASCII characters (default: False)."""
        ascii_mode = self.section.get("ensure_ascii", DEFAULT_ENSURE_ASCII)
        return bool(ascii_mode)

    @cached_property
    def encoding(self) -> str:
        """Get file encoding for JSON I/O (default: utf-8)."""
        enc = self.section.get("encoding", DEFAULT_ENCODING)
        return str(enc)

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
