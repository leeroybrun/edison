"""
Tests for T-021: Remove hardcoded validator counts from guidelines.

Guardrails:
- No guideline/agent content should mention a fixed "9-validator" (or similar) count.
- Validator references must point to the dynamic roster: AVAILABLE_VALIDATORS.md.
- Validation architecture must be described in tiers (Global, Critical, Specialized), not counts.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from edison.data import get_data_path


# Target files called out in the migration plan
GUIDELINE_FILES = [
    get_data_path("guidelines") / "shared" / "VALIDATION.md",
    get_data_path("guidelines") / "agents" / "VALIDATION_AWARENESS.md",
]

AGENT_VALIDATION_FILES = sorted(get_data_path("agents").glob("*.md"))

ALL_TARGET_FILES = GUIDELINE_FILES + AGENT_VALIDATION_FILES


@pytest.mark.parametrize("path", ALL_TARGET_FILES)
def test_validation_guides_have_no_hardcoded_validator_counts(path: Path) -> None:
    """Ensure hardcoded counts like '9 validators' or '9-validator' are absent."""

    content = path.read_text(encoding="utf-8")
    matches = re.findall(r"\b9[- ]?validator(?:s)?\b", content, flags=re.IGNORECASE)

    assert not matches, (
        f"Hardcoded validator count found in {path.name}: {sorted(set(matches))}"
    )


@pytest.mark.parametrize("path", ALL_TARGET_FILES)
def test_validation_guides_reference_dynamic_roster(path: Path) -> None:
    """Guidelines must point to the dynamic roster rather than embedding counts."""

    content = path.read_text(encoding="utf-8")

    assert "AVAILABLE_VALIDATORS.md" in content, (
        f"{path.name} must reference AVAILABLE_VALIDATORS.md for the validator roster"
    )


def test_validation_awareness_describes_tiered_architecture() -> None:
    """Validation architecture should be described by tiers, not fixed counts."""

    awareness = get_data_path("guidelines") / "agents" / "VALIDATION_AWARENESS.md"
    content = awareness.read_text(encoding="utf-8").lower()

    for tier in ("global", "critical", "comprehensive"):
        assert tier in content, (
            f"VALIDATION_AWARENESS.md must describe the {tier} validator tier"
        )
