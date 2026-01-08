"""Unified CLI output formatting utilities.

This module provides consistent output formatting for all Edison CLI commands,
supporting multiple output formats: markdown, yaml, text, and json.

LLM-facing commands default to markdown for better readability.
Config commands default to yaml for structured output.
JSON is available for machine consumption but NOT the default.
"""
from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from typing import Any, Dict, Optional

import yaml


class OutputFormat(Enum):
    """Supported output formats for CLI commands."""

    MARKDOWN = "markdown"
    YAML = "yaml"
    TEXT = "text"
    JSON = "json"


def add_format_flag(
    parser: argparse.ArgumentParser,
    *,
    default: str = "markdown",
) -> None:
    """Add --format flag to argument parser.

    Args:
        parser: ArgumentParser to add flag to
        default: Default format (markdown, yaml, text, or json)
    """
    parser.add_argument(
        "--format",
        choices=["markdown", "yaml", "text", "json"],
        default=default,
        help=f"Output format (default: {default})",
    )


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    """Add legacy --json flag for backwards compatibility.

    Args:
        parser: ArgumentParser to add flag to
    """
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON (shorthand for --format json)",
    )


def resolve_output_format(
    args: argparse.Namespace,
    *,
    default: OutputFormat = OutputFormat.MARKDOWN,
) -> OutputFormat:
    """Resolve output format from args namespace.

    Handles both new --format flag and legacy --json flag.
    --json takes precedence when set.

    Args:
        args: Parsed arguments namespace
        default: Default format when args lacks format attribute

    Returns:
        Resolved OutputFormat enum value
    """
    # Legacy --json flag takes precedence
    if getattr(args, "json", False):
        return OutputFormat.JSON

    # Check for --format flag
    format_str = getattr(args, "format", None)
    if format_str:
        try:
            return OutputFormat(format_str)
        except ValueError:
            return default

    return default


class OutputFormatter:
    """Unified output formatter for CLI commands."""

    def __init__(
        self,
        json_mode: bool = False,
        indent: int = 2,
        *,
        format: Optional[OutputFormat] = None,
    ):
        """Initialize formatter.

        Args:
            json_mode: If True, output JSON; otherwise output text (legacy)
            indent: JSON/YAML indentation level
            format: Output format (preferred over json_mode)
        """
        # Handle format parameter vs legacy json_mode
        if format is not None:
            self._format = format
            self._json_mode = format == OutputFormat.JSON
        elif json_mode:
            self._format = OutputFormat.JSON
            self._json_mode = True
        else:
            self._format = OutputFormat.MARKDOWN
            self._json_mode = False

        self.indent = indent

    @property
    def format(self) -> OutputFormat:
        """Get the current output format."""
        return self._format

    @property
    def json_mode(self) -> bool:
        """Get legacy json_mode flag."""
        return self._json_mode

    @classmethod
    def from_args(cls, args: argparse.Namespace, *, indent: int = 2) -> "OutputFormatter":
        """Create OutputFormatter from parsed arguments.

        Handles both new --format flag and legacy --json flag.

        Args:
            args: Parsed arguments namespace
            indent: Indentation level for JSON/YAML output

        Returns:
            Configured OutputFormatter instance
        """
        fmt = resolve_output_format(args)
        return cls(format=fmt, indent=indent)

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
                "code": error_code,
                "message": msg,
            }
            # In JSON mode, all machine-readable payloads go to stdout (including errors).
            print(json.dumps(output, indent=self.indent), file=sys.stdout)
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
        if self.json_mode:
            return
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

    def format_output(
        self,
        data: Dict[str, Any],
        *,
        template: Optional[str] = None,
    ) -> None:
        """Output data in the configured format.

        Args:
            data: Data dictionary to format and output
            template: Optional template name for markdown formatting
        """
        if self._format == OutputFormat.JSON:
            print(json.dumps(data, indent=self.indent, default=str))
        elif self._format == OutputFormat.YAML:
            print(yaml.dump(data, default_flow_style=False, sort_keys=False), end="")
        elif self._format == OutputFormat.MARKDOWN:
            self._format_markdown(data, template=template)
        else:  # TEXT
            self._format_text(data)

    def _format_markdown(
        self,
        data: Dict[str, Any],
        *,
        template: Optional[str] = None,
    ) -> None:
        """Format data as markdown.

        Args:
            data: Data dictionary to format
            template: Optional template name for specific formatting
        """
        lines: list[str] = []

        # Handle title if present
        if "title" in data:
            lines.append(f"# {data['title']}")
            lines.append("")

        for key, value in data.items():
            if key == "title":
                continue  # Already handled

            if isinstance(value, list):
                lines.append(f"## {key.replace('_', ' ').title()}")
                for item in value:
                    lines.append(f"- {item}")
                lines.append("")
            elif isinstance(value, dict):
                lines.append(f"## {key.replace('_', ' ').title()}")
                for k, v in value.items():
                    lines.append(f"- **{k}**: {v}")
                lines.append("")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}**: {value}")

        print("\n".join(lines))

    def _format_text(self, data: Dict[str, Any]) -> None:
        """Format data as plain text.

        Args:
            data: Data dictionary to format
        """
        lines: list[str] = []

        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")

        print("\n".join(lines))


__all__ = [
    "OutputFormat",
    "OutputFormatter",
    "add_format_flag",
    "add_json_flag",
    "resolve_output_format",
]
