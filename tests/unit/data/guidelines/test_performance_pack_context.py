"""
Tests for pack-aware performance validator documentation (T-049).

Ensures the performance validator guideline documents how to load and merge
pack-specific performance rules from the pack rule registries (T-032).
"""
from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/validators/critical/performance.md")


def test_performance_doc_has_pack_context_section():
    """Performance guideline must expose a pack-aware context section."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")

    assert "Pack-Specific Performance Context" in content, (
        "performance.md should include a Pack-Specific Performance Context section"
    )
    assert "pack performance rules" in content, "Pack context should describe pack performance rules"


def test_performance_doc_references_pack_registries_and_merge_strategy():
    """Documentation must explain registry locations and how core + pack rules merge."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8")

    expected_phrases = (
        ".edison/packs/<pack>/rules/registry.yml",
        "RulesRegistry.compose(packs=[",
        "merge core + pack performance rules",
    )
    for phrase in expected_phrases:
        assert phrase in content, f"Missing pack registry/merge guidance: {phrase}"
