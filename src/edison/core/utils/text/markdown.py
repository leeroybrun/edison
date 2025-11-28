#!/usr/bin/env python3
"""Markdown utilities for HTML comment metadata parsing.

Generic utilities for parsing and formatting HTML comment metadata
in markdown files. Used by entity repositories (Task, QA) for
serialization.

Format: <!-- Key: value -->
"""
from __future__ import annotations

from typing import Any, Optional


def parse_html_comment(line: str, key: str) -> Optional[str]:
    """Parse a metadata value from an HTML comment line.

    Extracts the value from a line in the format: <!-- Key: value -->

    Args:
        line: Line to parse (will be stripped)
        key: Metadata key to look for (case-sensitive)

    Returns:
        The value if found, None otherwise

    Example:
        >>> parse_html_comment("<!-- Owner: claude -->", "Owner")
        'claude'
        >>> parse_html_comment("<!-- Status: wip -->", "Status")
        'wip'
        >>> parse_html_comment("some other line", "Owner")
        None
    """
    stripped = line.strip()
    prefix = f"<!-- {key}:"
    suffix = "-->"

    if stripped.startswith(prefix) and stripped.endswith(suffix):
        # Extract value between prefix and suffix
        value = stripped[len(prefix):-len(suffix)].strip()
        return value

    return None


def format_html_comment(key: str, value: Any) -> str:
    """Format a metadata value as an HTML comment.

    Args:
        key: Metadata key
        value: Value to format (will be converted to string)

    Returns:
        Formatted HTML comment

    Example:
        >>> format_html_comment("Owner", "claude")
        '<!-- Owner: claude -->'
        >>> format_html_comment("Status", "wip")
        '<!-- Status: wip -->'
    """
    return f"<!-- {key}: {value} -->"


def parse_title(line: str) -> Optional[str]:
    """Parse a title from a markdown heading line.

    Extracts the title from a line starting with '# '

    Args:
        line: Line to parse (will be stripped)

    Returns:
        The title if found, None otherwise

    Example:
        >>> parse_title("# My Task Title")
        'My Task Title'
        >>> parse_title("## Not a top-level heading")
        None
        >>> parse_title("Regular text")
        None
    """
    stripped = line.strip()
    if stripped.startswith("# "):
        return stripped[2:].strip()
    return None


__all__ = [
    "parse_html_comment",
    "format_html_comment",
    "parse_title",
]
