"""
Tests for T-024: Restore TDD Verification Checklist.

These tests enforce that the TDD guideline contains the validator-facing
verification checklist, evidence requirements, and report template.
"""

from __future__ import annotations

from pathlib import Path

from edison.data import get_data_path


def _read_tdd_guideline() -> str:
    """Load the shared TDD guideline content."""

    tdd_path = get_data_path("guidelines") / "shared" / "TDD.md"
    assert tdd_path.exists(), "TDD guideline must exist at guidelines/shared/TDD.md"
    return tdd_path.read_text(encoding="utf-8")


def test_tdd_guideline_includes_verification_checklist_section() -> None:
    """Validators need a dedicated TDD verification checklist section."""

    content = _read_tdd_guideline()

    assert "## TDD Verification Checklist" in content, (
        "TDD.md must include a 'TDD Verification Checklist' section for validators"
    )


def test_tdd_verification_checklist_covers_red_green_refactor_items() -> None:
    """Checklist must enumerate RED/GREEN/REFACTOR verification items."""

    content = _read_tdd_guideline()

    required_checklist_items = [
        "- [ ] Tests exist in appropriate __tests__/ directory",
        "- [ ] Test file created BEFORE implementation (check git history)",
        "- [ ] Tests cover the requirements specified in task",
        "- [ ] Sub-agent showed tests failing initially",
        "- [ ] Failure messages indicate tests were actually testing something",
        "- [ ] No \"test.skip\" or commented-out tests",
        "- [ ] All tests now passing",
        "- [ ] No tests were removed or weakened to pass",
        "- [ ] Coverage meets minimum threshold (see quality.coverageTarget)",
        "- [ ] Tests still pass after refactoring",
        "- [ ] Code is cleaner without changing behavior",
        "- [ ] No new functionality added during refactor",
    ]

    missing = [item for item in required_checklist_items if item not in content]

    assert not missing, (
        "TDD verification checklist is missing required RED/GREEN/REFACTOR items: "
        + ", ".join(missing)
    )


def test_tdd_verification_includes_evidence_and_red_flags() -> None:
    """Checklist must include evidence requirements, report template, and red flags."""

    content = _read_tdd_guideline()

    evidence_markers = [
        '"tddCompliance"',
        '"redPhaseEvidence"',
        '"coverageThreshold"',
        '"violations"',
        '"verdict"',
        "Red Flags (TDD Violations)",
        "Immediate Rejection",
        "Needs Review",
    ]

    missing = [marker for marker in evidence_markers if marker not in content]

    assert not missing, (
        "TDD guideline must include evidence/report template and red-flag criteria. "
        "Missing: " + ", ".join(missing)
    )
