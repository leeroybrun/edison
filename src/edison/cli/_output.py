"""Unified CLI output formatting utilities.

This module provides consistent output formatting for all Edison CLI commands,
supporting both JSON and text output modes.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional


class OutputFormatter:
    """Unified output formatter for CLI commands."""

    def __init__(self, json_mode: bool = False, indent: int = 2):
        """Initialize formatter.

        Args:
            json_mode: If True, output JSON; otherwise output text
            indent: JSON indentation level
        """
        self.json_mode = json_mode
        self.indent = indent

    def success(
        self,
        data: Dict[str, Any],
        message: str,
        *,
        status: str = "success",
    ) -> None:
        """Output success result.

        Args:
            data: Result data dictionary
            message: Human-readable success message (used in text mode)
            status: Status string for JSON output
        """
        if self.json_mode:
            output = {"status": status, **data}
            print(json.dumps(output, indent=self.indent, default=str))
        else:
            print(message)

    def error(
        self,
        error: Exception,
        message: Optional[str] = None,
        *,
        error_code: str = "error",
    ) -> None:
        """Output error result.

        Args:
            error: The exception that occurred
            message: Optional human-readable message (defaults to str(error))
            error_code: Error code for JSON output
        """
        msg = message or str(error)
        if self.json_mode:
            output = {
                "error": error_code,
                "message": msg,
            }
            print(json.dumps(output, indent=self.indent), file=sys.stderr)
        else:
            print(f"Error: {msg}", file=sys.stderr)

    def json_output(self, data: Any) -> None:
        """Output raw JSON data.

        Args:
            data: Data to serialize as JSON
        """
        print(json.dumps(data, indent=self.indent, default=str))

    def text(self, message: str) -> None:
        """Output plain text message.

        Args:
            message: Message to output
        """
        print(message)

    def text_kv(self, key: str, value: Any, prefix: str = "  ") -> None:
        """Output key-value pair in text mode.

        Args:
            key: Key name
            value: Value to display
            prefix: Line prefix (default: two spaces for indentation)
        """
        if not self.json_mode:
            print(f"{prefix}{key}: {value}")


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON string.

    Args:
        data: Data to format
        indent: Indentation level

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, default=str)


def print_success(message: str) -> None:
    """Print success message with checkmark."""
    print(f"\u2713 {message}")


def print_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


__all__ = [
    "OutputFormatter",
    "format_json",
    "print_success",
    "print_error",
]
