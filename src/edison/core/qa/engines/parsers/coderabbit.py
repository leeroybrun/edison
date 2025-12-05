"""CodeRabbit CLI output parser.

Parses output from CodeRabbit CLI.
CodeRabbit with --prompt-only outputs plain text review prompts.
"""
from __future__ import annotations

from .base import ParseResult


def parse(output: str) -> ParseResult:
    """Parse CodeRabbit output.

    CodeRabbit CLI with --prompt-only outputs plain text.
    No JSON structure is available, so we return the text as-is.

    Args:
        output: Raw CLI stdout (plain text)

    Returns:
        ParseResult with text as response
    """
    if not output.strip():
        return ParseResult(
            response="",
            error="Empty output from CodeRabbit CLI",
            metadata=None,
        )

    # CodeRabbit outputs plain text, possibly with sections
    text = output.strip()

    # Try to detect if there's any structure (e.g., markdown sections)
    metadata = {}

    # Count sections if present (lines starting with #)
    sections = [line for line in text.split("\n") if line.strip().startswith("#")]
    if sections:
        metadata["section_count"] = len(sections)

    # Detect if it's a review summary vs full review
    if "## Summary" in text or "### Summary" in text:
        metadata["has_summary"] = True
    if "## Files" in text or "### Files" in text:
        metadata["has_files"] = True

    return ParseResult(
        response=text,
        error=None,
        metadata=metadata if metadata else None,
    )


__all__ = ["parse"]
