"""Parser registry for validator engine output parsing.

This module provides the parser infrastructure for the unified validator engine system.
Parsers convert CLI tool output into a standardized ParseResult format.

Each parser file exports a `parse(output: str) -> ParseResult` function.
The file name becomes the parser ID (e.g., codex.py → "codex").

Usage:
    from edison.core.qa.engines.parsers import get_parser, ensure_parsers_loaded

    # Ensure parsers are loaded
    ensure_parsers_loaded(project_root)

    # Get a specific parser
    parser = get_parser("codex")
    if parser:
        result = parser(raw_output)

Built-in parsers:
    - codex: OpenAI Codex CLI (JSONL events)
    - gemini: Google Gemini CLI (JSON)
    - claude: Anthropic Claude Code CLI (JSON)
    - auggie: Augment Code CLI (JSON)
    - coderabbit: CodeRabbit CLI (plain text)
    - plain_text: Fallback for unstructured output
"""
from __future__ import annotations

from .base import ParseResult, ParserProtocol
from .loader import (
    ensure_parsers_loaded,
    get_parser,
    list_parsers,
    load_parsers,
    register_parser,
)

__all__ = [
    "ParseResult",
    "ParserProtocol",
    "ensure_parsers_loaded",
    "get_parser",
    "list_parsers",
    "load_parsers",
    "register_parser",
]

