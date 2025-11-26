"""Regression tests for the TDD troubleshooting guidance."""

from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/guidelines/shared/TDD.md")
SECTION_MARKER = "## TDD Troubleshooting"


def _extract_section(text: str, marker: str) -> str:
    """Return the text for a heading until the next heading at the same level."""

    start = text.find(marker)
    assert start != -1, f"TDD guide is missing the section: {marker}"

    section = text[start:]
    delimiter = "\n## " if marker.startswith("## ") else "\n### "
    if delimiter in section[len(marker) :]:
        section = section.split(delimiter, maxsplit=1)[0]
    return section


def test_troubleshooting_section_lists_core_scenarios() -> None:
    """Troubleshooting section must enumerate the common failure cases."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")
    section = _extract_section(content, SECTION_MARKER)

    for heading in (
        "### Test Won't Fail (RED phase)",
        "### Test Won't Pass (GREEN phase)",
        "### Refactor Breaks Tests",
        "### Flaky Tests",
    ):
        assert heading in section, f"Missing troubleshooting scenario: {heading}"


def test_troubleshooting_entries_include_symptom_cause_fix() -> None:
    """Each troubleshooting entry must describe symptom, cause, and fix."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")
    section = _extract_section(content, SECTION_MARKER)

    for heading in (
        "### Test Won't Fail (RED phase)",
        "### Test Won't Pass (GREEN phase)",
        "### Refactor Breaks Tests",
        "### Flaky Tests",
    ):
        entry = _extract_section(section, heading)
        for label in ("Symptom", "Cause", "Fix"):
            assert (
                f"**{label}**" in entry or f"**{label}s**" in entry
            ), f"Entry '{heading}' missing {label.lower()} description"
