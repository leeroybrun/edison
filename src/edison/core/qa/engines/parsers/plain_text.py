"""Plain text output parser (fallback).

Handles raw text output from tools that don't produce structured output.
This is the default parser when no specific parser is configured.
"""
from __future__ import annotations

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse plain text output.

    Simply strips whitespace and returns as response.
    Used as fallback for tools without structured output.

    Args:
        output: Raw CLI stdout

    Returns:
        ParseResult with cleaned text as response
    """
    return ParseResult(
        response=output.strip(),
        error=None,
        metadata=None,
    )


__all__ = ["parse"]

