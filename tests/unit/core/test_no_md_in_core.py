"""Guardrail: no markdown content should live in src/edison/core.

Only the package README.md is permitted; all other .md files belong in
src/edison/data/ to keep core strictly Python-only.
"""
from __future__ import annotations

from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[2] / "src" / "edison" / "core"


def _markdown_files() -> list[Path]:
    """List all markdown files under core/, excluding the root README.md."""
    allowed_readme = CORE_DIR / "README.md"
    return [
        path
        for path in CORE_DIR.rglob("*.md")
        if path.resolve() != allowed_readme.resolve()
    ]


def test_core_has_no_markdown_files() -> None:
    markdown_files = _markdown_files()
    assert markdown_files == [], (
        "Markdown content belongs in src/edison/data/. Found: "
        + ", ".join(str(p.relative_to(CORE_DIR)) for p in markdown_files)
    )
