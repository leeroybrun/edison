"""Post-create UX helpers for artifact-producing commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from edison.core.artifacts.required_fill import find_missing_required_sections


def format_required_fill_next_steps(
    markdown: str,
    *,
    display_path: str | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> str | None:
    """Format a human-readable next-steps hint for required-fill artifacts.

    Returns None when the artifact has no REQUIRED FILL markers or no missing sections.
    """
    missing = find_missing_required_sections(markdown, cfg=cfg)
    if not missing:
        return None

    path_hint = f"  1. Open: @{display_path}" if display_path else "  1. Open the artifact file"
    sections = ", ".join(missing)

    return "\n".join(
        [
            "Next steps:",
            path_hint,
            f"  2. Fill required sections: {sections}",
        ]
    )


def format_required_fill_next_steps_for_file(
    path: Path,
    *,
    display_path: str | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> str | None:
    """Like format_required_fill_next_steps(), but reads from disk (fail-open)."""
    try:
        content = path.read_text(encoding="utf-8", errors="strict")
    except Exception:
        return None
    return format_required_fill_next_steps(content, display_path=display_path, cfg=cfg)


__all__ = ["format_required_fill_next_steps", "format_required_fill_next_steps_for_file"]
