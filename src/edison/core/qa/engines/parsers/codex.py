"""Codex CLI output parser.

Parses JSONL events from OpenAI Codex CLI, extracting the final agent message.
Codex outputs streaming JSONL events, with the final response in an
'item.completed' event of type 'agent_message'.
"""
from __future__ import annotations

import json

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse Codex JSONL events, extract final agent_message.

    Codex CLI streams JSONL events. We need to find the last
    'item.completed' event with type 'agent_message' to get
    the final response.

    Args:
        output: Raw CLI stdout (JSONL events, one per line)

    Returns:
        ParseResult with extracted response or error
    """
    if not output.strip():
        return ParseResult(
            response="",
            error="Empty output from Codex CLI",
            metadata=None,
        )

    lines = output.strip().split("\n")

    # Process lines in reverse to find the last agent message
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)

            # Look for item.completed events with agent_message
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    text = item.get("text", "")
                    return ParseResult(
                        response=text,
                        error=None,
                        metadata={
                            "event_type": "item.completed",
                            "item_type": "agent_message",
                        },
                    )

            # Also check for message events (alternative format)
            if event.get("type") == "message":
                content = event.get("content", "")
                if content:
                    return ParseResult(
                        response=content,
                        error=None,
                        metadata={"event_type": "message"},
                    )

        except json.JSONDecodeError:
            # Skip non-JSON lines (could be progress output)
            continue

    # If no structured message found, return the full output
    return ParseResult(
        response=output.strip(),
        error="No agent_message found in Codex output, returning raw output",
        metadata={"fallback": True},
    )


__all__ = ["parse"]

