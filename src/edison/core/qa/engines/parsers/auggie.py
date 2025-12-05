"""Auggie CLI output parser.

Parses JSON output from Augment Code's auggie CLI.
Auggie outputs structured JSON with --output-format json flag.
"""
from __future__ import annotations

import json

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse Auggie JSON output.

    Auggie (Augment Code CLI) outputs JSON with structured review results.
    The response is typically in 'response', 'result', or 'output' field.

    Args:
        output: Raw CLI stdout (JSON)

    Returns:
        Standardized ParseResult
    """
    if not output.strip():
        return ParseResult(
            response="",
            error="Empty output from Auggie CLI",
            metadata=None,
        )

    try:
        data = json.loads(output)

        # Auggie may use various field names
        response = (
            data.get("response", "")
            or data.get("result", "")
            or data.get("output", "")
            or data.get("content", "")
        )

        # Check for error field
        error = data.get("error")

        # Extract metadata
        metadata = {}
        for key in ["model", "cost", "tokens", "duration", "status"]:
            if key in data:
                metadata[key] = data[key]

        # If data has 'findings' or 'issues', include as metadata
        if "findings" in data:
            metadata["findings"] = data["findings"]
        if "issues" in data:
            metadata["issues"] = data["issues"]

        return ParseResult(
            response=response,
            error=error,
            metadata=metadata if metadata else None,
        )

    except json.JSONDecodeError as e:
        # Return raw output if JSON parsing fails
        return ParseResult(
            response=output.strip(),
            error=f"Failed to parse JSON: {e}",
            metadata={"fallback": True},
        )


__all__ = ["parse"]
