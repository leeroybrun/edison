"""Structured report I/O helpers.

Edison stores structured workflow artifacts as Markdown with YAML frontmatter:
- LLM-readable (Markdown body)
- Machine-readable (YAML frontmatter)

This module intentionally supports **only** the canonical Markdown+frontmatter
format (no legacy JSON fallbacks).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import read_text, write_text
from edison.core.utils.text import ParsedDocument, format_frontmatter, parse_frontmatter


def _as_mapping(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


def read_structured_report(path: Path) -> Dict[str, Any]:
    """Read a structured report from ``path`` (Markdown+frontmatter only).

    Returns an empty dict when:
    - file is missing
    - file is not Markdown
    - frontmatter is missing/invalid
    """
    try:
        if not path.exists():
            return {}
        if path.suffix.lower() not in {".md", ".markdown"}:
            return {}
        content = read_text(path)
        doc = parse_frontmatter(content)
        return _as_mapping(doc.frontmatter) if doc.frontmatter else {}
    except Exception:
        return {}


def _read_md_frontmatter_and_body(path: Path) -> ParsedDocument:
    """Read Markdown report and parse YAML frontmatter.

    Returns an empty-frontmatter ParsedDocument on missing file.
    Raises ValueError on invalid YAML frontmatter.
    """
    if not path.exists():
        return ParsedDocument(frontmatter={}, content="", raw_frontmatter="")
    content = read_text(path)
    return parse_frontmatter(content)


def write_structured_report(
    path: Path,
    data: Dict[str, Any],
    *,
    body: Optional[str] = None,
    preserve_existing_body: bool = True,
) -> None:
    """Write a structured report to ``path``.

    - ``*.md``: writes YAML frontmatter + Markdown body atomically.

    When writing Markdown, the default behavior is to preserve any existing
    body unless an explicit ``body`` is provided.
    """
    suffix = path.suffix.lower()
    if suffix not in {".md", ".markdown"}:
        raise ValueError(f"Unsupported report format: {path.name}")

    existing_body = ""
    if preserve_existing_body and path.exists():
        try:
            doc = _read_md_frontmatter_and_body(path)
            existing_body = doc.content
        except Exception:
            existing_body = ""

    final_body = body if body is not None else existing_body
    content = format_frontmatter(data, exclude_none=True) + (final_body or "")
    write_text(path, content)
