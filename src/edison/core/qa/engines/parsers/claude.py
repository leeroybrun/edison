"""Claude CLI output parser.

Parses JSON output from Anthropic Claude Code CLI.
Claude outputs JSON with --output-format json flag.
"""
from __future__ import annotations

import json

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse Claude JSON output.

    Claude Code CLI with --output-format json outputs structured JSON.
    The response is typically in 'result' or 'response' field.

    Args:
        output: Raw CLI stdout (JSON)

    Returns:
        Standardized ParseResult
    """
    if not output.strip():
        return ParseResult(
            response="",
            error="Empty output from Claude CLI",
            metadata=None,
        )

    try:
        data = json.loads(output)

        # Claude may use 'result', 'response', 'content', or 'text'
        response = (
            data.get("result", "")
            or data.get("response", "")
            or data.get("content", "")
            or data.get("text", "")
        )

        # Check for error field
        error = data.get("error")

        # Extract any metadata
        metadata = {}
        for key in ["model", "usage", "stop_reason", "id"]:
            if key in data:
                metadata[key] = data[key]

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
