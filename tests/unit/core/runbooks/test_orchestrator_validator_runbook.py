"""
T-033: Guardrails for the orchestrator-validator runbook.

Verifies the runbook exists and documents key behaviors:
- references the dynamic validator roster (AVAILABLE_VALIDATORS.md)
- explains how to trigger validators
- explains how to handle rejection cycles
- documents escalation when maximum validation rounds are exceeded
"""
from __future__ import annotations

from pathlib import Path

import pytest


RUNBOOK_PATH = (
    Path(__file__)
    .resolve()
    .parents[4]
    / "src"
    / "edison"
    / "core"
    / "runbooks"
    / "ORCHESTRATOR_VALIDATOR_RUNBOOK.md"
)


@pytest.fixture(scope="module")
def runbook_content() -> str:
    """Load the runbook content once for this module."""
    assert RUNBOOK_PATH.exists(), f"Missing runbook at {RUNBOOK_PATH}"
    return RUNBOOK_PATH.read_text(encoding="utf-8")


def test_runbook_file_exists() -> None:
    """Runbook must be present at the expected path."""
    assert RUNBOOK_PATH.exists(), f"Missing runbook at {RUNBOOK_PATH}"


def test_runbook_references_dynamic_validator_roster(runbook_content: str) -> None:
    """Runbook should point to AVAILABLE_VALIDATORS.md instead of hardcoding validators."""
    assert "AVAILABLE_VALIDATORS.md" in runbook_content, (
        "Runbook must reference AVAILABLE_VALIDATORS.md (dynamic roster) "
        "instead of embedding validator names or counts."
    )


def test_runbook_covers_triggers_and_rejections(runbook_content: str) -> None:
    """
    Ensure the runbook includes operational guidance for triggering validators
    and handling rejection cycles.
    """
    content_lower = runbook_content.lower()

    assert "trigger" in content_lower and "validator" in content_lower, (
        "Runbook must explain how orchestrators trigger validators."
    )
    assert "rejection" in content_lower or "reject" in content_lower, (
        "Runbook must describe how to handle validator rejections."
    )


def test_runbook_covers_escalation_protocol(runbook_content: str) -> None:
    """Runbook must describe escalation when the maximum validation rounds are exceeded."""
    content_lower = runbook_content.lower()

    assert "max round" in content_lower or "maximum round" in content_lower, (
        "Runbook must call out a max-rounds threshold before escalation."
    )
    assert "escalat" in content_lower, "Runbook must include an escalation protocol."
