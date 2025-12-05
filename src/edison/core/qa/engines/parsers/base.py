"""Base types for parser functions.

This module defines the standardized interface for CLI output parsers.
All parsers must return a ParseResult and implement the parse() function.
"""
from __future__ import annotations

from typing import Any, Protocol, TypedDict


class ParseResult(TypedDict, total=False):
    """Standardized parser output.

    All parsers must return this structure for consistent handling
    across different CLI tools.

    Attributes:
        response: Main response text (required)
        error: Error message if parsing failed (optional)
        metadata: Tool-specific data like stats, cost, etc. (optional)
    """

    response: str
    error: str | None
    metadata: dict[str, Any] | None


class ParserProtocol(Protocol):
    """Protocol for parser functions.

    Each parser file must export a `parse` function that adheres to this protocol.
    """

    def __call__(self, output: str) -> ParseResult:
        """Parse CLI output and return standardized result.

        Args:
            output: Raw CLI stdout

        Returns:
            Standardized ParseResult
        """
        ...


__all__ = [
    "ParseResult",
    "ParserProtocol",
]

