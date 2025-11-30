"""Domain-specific configuration for CLI output formatting.

Provides cached access to CLI configuration including JSON output,
table formatting, confirmation prompts, and status messages.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig

# Default configuration values
DEFAULT_JSON_INDENT = 2
DEFAULT_JSON_SORT_KEYS = True
DEFAULT_JSON_ENSURE_ASCII = False
DEFAULT_TABLE_PADDING = 1
DEFAULT_TABLE_COLUMN_GAP = 2
DEFAULT_CONFIRM_ASSUME_YES_ENV = "EDISON_ASSUME_YES"
DEFAULT_SUCCESS_PREFIX = "[OK]"
DEFAULT_ERROR_PREFIX = "[ERR]"
DEFAULT_WARNING_PREFIX = "[WARN]"
DEFAULT_USE_COLOR = False


class CLIConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for CLI output.

    Provides typed, cached access to CLI configuration including:
    - JSON output formatting
    - Table formatting (padding, spacing)
    - Confirmation prompt defaults
    - Output message prefixes

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "cli"

    @cached_property
    def _json_config(self) -> Dict[str, Any]:
        """Get JSON output configuration."""
        return self.section.get("json", {}) or {}

    @cached_property
    def _table_config(self) -> Dict[str, Any]:
        """Get table formatting configuration."""
        return self.section.get("table", {}) or {}

    @cached_property
    def _confirm_config(self) -> Dict[str, Any]:
        """Get confirmation prompt configuration."""
        return self.section.get("confirm", {}) or {}

    @cached_property
    def _output_config(self) -> Dict[str, Any]:
        """Get output message configuration."""
        return self.section.get("output", {}) or {}

    # --- JSON Output Settings ---
    @cached_property
    def json_indent(self) -> int:
        """Get JSON indentation level (default: 2)."""
        indent = self._json_config.get("indent", DEFAULT_JSON_INDENT)
        return int(indent)

    @cached_property
    def json_sort_keys(self) -> bool:
        """Get whether to sort JSON object keys (default: True)."""
        sort = self._json_config.get("sort_keys", DEFAULT_JSON_SORT_KEYS)
        return bool(sort)

    @cached_property
    def json_ensure_ascii(self) -> bool:
        """Get whether to escape non-ASCII in JSON (default: False)."""
        ascii_mode = self._json_config.get("ensure_ascii", DEFAULT_JSON_ENSURE_ASCII)
        return bool(ascii_mode)

    # --- Table Formatting Settings ---
    @cached_property
    def table_padding(self) -> int:
        """Get table cell padding (default: 1)."""
        padding = self._table_config.get("padding", DEFAULT_TABLE_PADDING)
        return int(padding)

    @cached_property
    def table_column_gap(self) -> int:
        """Get spacing between table columns (default: 2)."""
        gap = self._table_config.get("column_gap", DEFAULT_TABLE_COLUMN_GAP)
        return int(gap)

    # --- Confirmation Prompt Settings ---
    @cached_property
    def confirm_assume_yes_env(self) -> str:
        """Get environment variable name for auto-confirm (default: EDISON_ASSUME_YES)."""
        env_var = self._confirm_config.get("assume_yes_env", DEFAULT_CONFIRM_ASSUME_YES_ENV)
        return str(env_var)

    # --- Output Message Settings ---
    @cached_property
    def success_prefix(self) -> str:
        """Get success message prefix (default: [OK])."""
        prefix = self._output_config.get("success_prefix", DEFAULT_SUCCESS_PREFIX)
        return str(prefix)

    @cached_property
    def error_prefix(self) -> str:
        """Get error message prefix (default: [ERR])."""
        prefix = self._output_config.get("error_prefix", DEFAULT_ERROR_PREFIX)
        return str(prefix)

    @cached_property
    def warning_prefix(self) -> str:
        """Get warning message prefix (default: [WARN])."""
        prefix = self._output_config.get("warning_prefix", DEFAULT_WARNING_PREFIX)
        return str(prefix)

    @cached_property
    def use_color(self) -> bool:
        """Get whether to use colored output (default: False)."""
        color = self._output_config.get("use_color", DEFAULT_USE_COLOR)
        return bool(color)

    def get_json_config(self) -> Dict[str, Any]:
        """Get all JSON formatting settings as a dict.

        Returns:
            Dict with indent, sort_keys, ensure_ascii.
        """
        return {
            "indent": self.json_indent,
            "sort_keys": self.json_sort_keys,
            "ensure_ascii": self.json_ensure_ascii,
        }

    def get_table_config(self) -> Dict[str, Any]:
        """Get all table formatting settings as a dict.

        Returns:
            Dict with padding, column_gap.
        """
        return {
            "padding": self.table_padding,
            "column_gap": self.table_column_gap,
        }

    def get_confirm_config(self) -> Dict[str, Any]:
        """Get all confirmation settings as a dict.

        Returns:
            Dict with assume_yes_env.
        """
        return {
            "assume_yes_env": self.confirm_assume_yes_env,
        }

    def get_output_config(self) -> Dict[str, Any]:
        """Get all output message settings as a dict.

        Returns:
            Dict with success_prefix, error_prefix, warning_prefix, use_color.
        """
        return {
            "success_prefix": self.success_prefix,
            "error_prefix": self.error_prefix,
            "warning_prefix": self.warning_prefix,
            "use_color": self.use_color,
        }


__all__ = [
    "CLIConfig",
]
