"""Gemini CLI output parser.

Parses JSON output from Google Gemini CLI.
Gemini outputs: {response, stats, error}
"""
from __future__ import annotations

import json

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse Gemini JSON output: {response, stats, error}.

    Args:
        output: Raw CLI stdout (JSON)

    Returns:
        Standardized ParseResult
    """
    if not output.strip():
        return ParseResult(
            response="",
            error="Empty output from Gemini CLI",
            metadata=None,
        )

    try:
        data = json.loads(output)

        # Handle standard Gemini response format
        response = data.get("response", "")

        # Also check for 'text' or 'content' fields (alternative formats)
        if not response:
            response = data.get("text", data.get("content", ""))

        # Extract stats if present
        stats = data.get("stats")
        error = data.get("error")

        return ParseResult(
            response=response,
            error=error,
            metadata={"stats": stats} if stats else None,
        )

    except json.JSONDecodeError as e:
        # Return raw output if JSON parsing fails
        return ParseResult(
            response=output.strip(),
            error=f"Failed to parse JSON: {e}",
            metadata={"fallback": True},
        )


__all__ = ["parse"]
