from __future__ import annotations

import re
from pathlib import Path

from edison.data import get_data_path

FILLER_PATTERNS = [
    re.compile(r"Additional note \d+:", re.IGNORECASE),
    re.compile(r"Note \d+:", re.IGNORECASE),
]


def _iter_markdown_files() -> list[Path]:
    """Iterate over all markdown files in bundled guidelines."""
    files: list[Path] = []

    # Get bundled guidelines from package data
    guidelines_root = get_data_path("guidelines")

    # Recursively find all .md files
    for md_file in guidelines_root.rglob("*.md"):
        if md_file.name.lower() != "readme.md":
            files.append(md_file)

    return sorted(files)


def test_guidelines_have_no_additional_note_filler() -> None:
    """
    FINDING-0XY.1.5: Remove filler lines like 'Additional note N: ...'

    Guardrail: any future re-introduction of generator-style padding lines
    must immediately fail tests.
    """
    offenders: list[str] = []
    guidelines_root = get_data_path("guidelines")

    for path in _iter_markdown_files():
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if any(p.search(stripped) for p in FILLER_PATTERNS):
                offenders.append(f"{path.relative_to(guidelines_root)}:{lineno} - {stripped}")

    assert not offenders, (
        "Found filler-style lines in core guidelines/guides; remove generator padding:\n"
        + "\n".join(offenders)
    )



