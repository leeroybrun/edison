"""Lightweight text template rendering.

Used for document scaffolds (TASK/QA templates, setup templates).

Goals:
- Keep templates readable in Markdown
- Prefer Jinja2 when available (optional dependency)
- Provide a safe regex fallback when Jinja2 is unavailable
"""

from __future__ import annotations

import re
from typing import Any, Dict

try:  # Optional dependency; fallback rendering when missing
    from jinja2 import Environment  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    Environment = None  # type: ignore[assignment]


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
_FULL_VAR_RE = re.compile(r"^\{\{\s*([a-zA-Z0-9_]+)\s*\}\}$")
_FRONTMATTER_BLOCK_RE = re.compile(r"^---\s*\n.*?\n---\s*\n?", re.DOTALL)


def strip_frontmatter_block(text: str) -> str:
    """Remove a leading YAML frontmatter block without parsing it."""
    return _FRONTMATTER_BLOCK_RE.sub("", text, count=1)


def render_template_text(text: str, context: Dict[str, Any]) -> str:
    """Render ``text`` using Jinja2 if available, else a simple {{var}} replacer."""
    if Environment is not None:
        try:
            # Many Edison templates use control blocks on their own lines.
            # Without trimming, those tag-only lines become empty lines.
            env = Environment(trim_blocks=True, lstrip_blocks=True)
            return env.from_string(text).render(**context)
        except Exception:
            pass

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        val = context.get(key, "")
        return "" if val is None else str(val)

    return _VAR_RE.sub(repl, text)


def render_template_value(value: str, context: Dict[str, Any]) -> Any:
    """Render a single value with context substitution.

    Supports:
    - Full variable replacement: ``"{{ var }}"`` returns context[var] (not coerced to str)
    - Inline rendering for larger strings (coerces values to strings)
    """
    full_match = _FULL_VAR_RE.fullmatch(value)
    if full_match:
        key = full_match.group(1)
        return context.get(key, "")

    return render_template_text(value, context)


def render_template_dict(template_obj: Any, context: Dict[str, Any]) -> Any:
    """Recursively render templates in nested dict/list structures."""
    if isinstance(template_obj, dict):
        return {k: render_template_dict(v, context) for k, v in template_obj.items()}
    if isinstance(template_obj, list):
        return [render_template_dict(v, context) for v in template_obj]
    if isinstance(template_obj, str):
        return render_template_value(template_obj, context)
    return template_obj


__all__ = [
    "strip_frontmatter_block",
    "render_template_text",
    "render_template_value",
    "render_template_dict",
]
