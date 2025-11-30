"""Domain-specific configuration for CLI output formatting.

Provides cached access to CLI configuration including table formatting,
confirmation prompts, and status messages.

Note: JSON formatting settings are in JSONIOConfig (not duplicated here).
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig


class CLIConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for CLI output.

    Provides typed, cached access to CLI configuration including:
    - Table formatting (padding, spacing)
    - Confirmation prompt defaults
    - Output message prefixes

    Note: JSON formatting is handled by JSONIOConfig to avoid duplication.

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "cli"

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

    # --- Table Formatting Settings ---
    @cached_property
    def table_padding(self) -> int:
        """Get table cell padding."""
        return int(self._table_config["padding"])

    @cached_property
    def table_column_gap(self) -> int:
        """Get spacing between table columns."""
        return int(self._table_config["column_gap"])

    # --- Confirmation Prompt Settings ---
    @cached_property
    def confirm_assume_yes_env(self) -> str:
        """Get environment variable name for auto-confirm."""
        return str(self._confirm_config["assume_yes_env"])

    # --- Output Message Settings ---
    @cached_property
    def success_prefix(self) -> str:
        """Get success message prefix."""
        return str(self._output_config["success_prefix"])

    @cached_property
    def error_prefix(self) -> str:
        """Get error message prefix."""
        return str(self._output_config["error_prefix"])

    @cached_property
    def warning_prefix(self) -> str:
        """Get warning message prefix."""
        return str(self._output_config["warning_prefix"])

    @cached_property
    def use_color(self) -> bool:
        """Get whether to use colored output."""
        return bool(self._output_config["use_color"])

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
