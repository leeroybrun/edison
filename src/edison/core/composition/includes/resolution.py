"""Public include-resolution helpers.

This module exists to provide a small, stable API for tests and tooling that want
to render template includes outside of the full `TemplateEngine`.

Important:
- The canonical include syntax and behavior is implemented by the TemplateEngine
  transformers in `edison.core.composition.transformers.includes`.
- This wrapper intentionally reuses those transformers (no duplicate parsing
  logic), and fails closed when include/section resolution emits an error marker.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from edison.core.composition.transformers.base import TransformContext
from edison.core.composition.transformers.includes import IncludeResolver, SectionExtractor


class ComposeError(RuntimeError):
    """Raised when include/section resolution fails (fail-closed)."""


@dataclass(frozen=True)
class IncludeResolutionResult:
    content: str
    dependencies: List[Path]


def _detect_data_root(base_file: Path) -> Optional[Path]:
    """Try to locate a data root (containing config/ + guidelines/) above base_file."""
    for parent in [base_file.parent, *base_file.parents]:
        try:
            if (parent / "config").is_dir() and (parent / "guidelines").is_dir():
                return parent
        except OSError:
            continue
    return None


def resolve_includes(content: str, base_file: Path) -> Tuple[str, List[Path]]:
    """Resolve {{include:*}}, {{include-optional:*}}, and {{include-section:*}}.

    This is a convenience wrapper for tests and static validation.

    Args:
        content: Template content.
        base_file: The file the content came from (used to infer a sensible source_dir).

    Returns:
        (rendered_content, dependency_paths)

    Raises:
        ComposeError: When resolution produces any `<!-- ERROR: ... -->` marker.
    """
    source_dir = _detect_data_root(base_file) or base_file.parent

    ctx = TransformContext(
        config={},
        active_packs=[],
        project_root=None,
        source_dir=source_dir,
        include_provider=None,
        strip_section_markers=False,
    )

    rendered = IncludeResolver().transform(content, ctx)
    rendered = SectionExtractor().transform(rendered, ctx)

    # Fail closed on any include/section resolution error marker.
    if "<!-- ERROR:" in rendered:
        # Keep the exception short but actionable.
        snippet = rendered.split("<!-- ERROR:", 1)[1]
        first_line = snippet.split("-->", 1)[0].strip()
        raise ComposeError(f"Include resolution failed: {first_line}")

    deps = sorted({Path(p) for p in ctx.includes_resolved})
    return rendered, deps


__all__ = ["ComposeError", "IncludeResolutionResult", "resolve_includes"]








