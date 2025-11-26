"""Regression tests for the Code Smell Checklist in QUALITY.md."""

from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/guidelines/shared/QUALITY.md")


def _extract_code_smell_section(text: str) -> str:
    """Return the Code Smell Checklist section text."""

    marker = "## Code Smell Checklist"
    start = text.find(marker)
    assert start != -1, "QUALITY.md is missing the Code Smell Checklist section"

    section = text[start:]
    # Stop at the next top-level heading (## ) if present
    delimiter = "\n## "
    if delimiter in section[len(marker) :]:
        section = section.split(delimiter, maxsplit=1)[0]
    return section


def test_quality_doc_includes_all_checklist_categories():
    """Ensure the checklist and its required categories are present."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")
    section = _extract_code_smell_section(content)

    for heading in (
        "### Naming Smells",
        "### Function Smells",
        "### Class Smells",
        "### Comment Smells",
        "### Duplication Smells",
        "### Architecture Smells",
    ):
        assert heading in section, f"Missing checklist category: {heading}"


def test_quality_doc_contains_at_least_40_code_smell_items():
    """Checklist must enumerate a broad set of code smell items (>=40)."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")
    section = _extract_code_smell_section(content)

    items = [line for line in section.splitlines() if line.strip().startswith("- ")]
    assert len(items) >= 40, f"Expected >=40 checklist items, found {len(items)}"
