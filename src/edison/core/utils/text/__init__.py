#!/usr/bin/env python3
"""Text processing utilities.

This package provides text processing utilities for composition and validation:

- core: DRY duplication detection (shingling), conditional includes
- markdown: HTML comment metadata parsing for entity serialization
- frontmatter: YAML frontmatter parsing

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

# Re-export from markdown module
from .markdown import (
    parse_html_comment,
    format_html_comment,
    parse_title,
)

# Re-export from frontmatter module
from .frontmatter import (
    ParsedDocument,
    parse_frontmatter,
    format_frontmatter,
    extract_frontmatter_batch,
    has_frontmatter,
    update_frontmatter,
    FRONTMATTER_PATTERN,
)

from .templates import (
    strip_frontmatter_block,
    render_template_text,
    render_template_value,
    render_template_dict,
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
    # Anchors (backwards compatibility)
    "AnchorNotFoundError",
    "extract_anchor_content",
    # Markdown
    "parse_html_comment",
    "format_html_comment",
    "parse_title",
    # Frontmatter
    "ParsedDocument",
    "parse_frontmatter",
    "format_frontmatter",
    "extract_frontmatter_batch",
    "has_frontmatter",
    "update_frontmatter",
    "FRONTMATTER_PATTERN",
    # Templates
    "strip_frontmatter_block",
    "render_template_text",
    "render_template_value",
    "render_template_dict",
]
