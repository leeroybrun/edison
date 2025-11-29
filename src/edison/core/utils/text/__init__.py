#!/usr/bin/env python3
"""Text processing utilities.

This package provides text processing utilities for composition and validation:

- core: DRY duplication detection (shingling), conditional includes
- anchors: ANCHOR marker extraction from guideline files
- markdown: HTML comment metadata parsing for entity serialization

All exports are available directly from this package for backward compatibility.
"""
from __future__ import annotations

# Re-export from core module
from .core import (
    get_engine_version,
    dry_duplicate_report,
    render_conditional_includes,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
    _split_paragraphs,
    _paragraph_shingles,
)

# Lazy ENGINE_VERSION for backward compatibility
def __getattr__(name: str):
    if name == "ENGINE_VERSION":
        return get_engine_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Re-export from anchors module
from .anchors import (
    AnchorNotFoundError,
    extract_anchor_content,
)

# Re-export from markdown module
from .markdown import (
    parse_html_comment,
    format_html_comment,
    parse_title,
)


__all__ = [
    # Core
    "ENGINE_VERSION",
    "get_engine_version",
    "dry_duplicate_report",
    "render_conditional_includes",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    "_split_paragraphs",
    "_paragraph_shingles",
    # Anchors
    "AnchorNotFoundError",
    "extract_anchor_content",
    # Markdown
    "parse_html_comment",
    "format_html_comment",
    "parse_title",
]
