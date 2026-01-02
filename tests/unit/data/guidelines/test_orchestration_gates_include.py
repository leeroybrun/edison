"""Tests for ORCHESTRATION_GATES include-only file.

Verifies that orchestration gates are durable across context compaction
by existing as an include-only file with proper sections.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INCLUDES_DIR = ROOT / "src" / "edison" / "data" / "guidelines" / "includes"
ORCHESTRATION_GATES_PATH = INCLUDES_DIR / "ORCHESTRATION_GATES.md"


def test_orchestration_gates_file_exists() -> None:
    """ORCHESTRATION_GATES.md must exist in guidelines/includes/."""
    assert ORCHESTRATION_GATES_PATH.exists(), (
        f"Expected ORCHESTRATION_GATES.md at {ORCHESTRATION_GATES_PATH.relative_to(ROOT)}"
    )


def test_orchestration_gates_is_include_only() -> None:
    """ORCHESTRATION_GATES.md must be marked as include-only (not directly readable)."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    assert "include-section" in text.lower(), "Expected include-section hint"
    assert "do not read directly" in text.lower(), "Expected privacy warning"


def test_orchestration_gates_has_orchestrator_session_long_section() -> None:
    """ORCHESTRATION_GATES.md must have #orchestrator-session-long section for constitution."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    assert "<!-- section: orchestrator-session-long -->" in text, (
        "Expected #orchestrator-session-long section marker"
    )
    assert "<!-- /section: orchestrator-session-long -->" in text, (
        "Expected #orchestrator-session-long end marker"
    )


def test_orchestration_gates_has_start_bootstrap_section() -> None:
    """ORCHESTRATION_GATES.md must have #start-bootstrap section for start prompts."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    assert "<!-- section: start-bootstrap -->" in text, (
        "Expected #start-bootstrap section marker"
    )
    assert "<!-- /section: start-bootstrap -->" in text, (
        "Expected #start-bootstrap end marker"
    )


def test_orchestrator_session_long_contains_delegation_guidance() -> None:
    """The orchestrator-session-long section must include delegation-first guidance."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    # Extract the section content
    start = text.find("<!-- section: orchestrator-session-long -->")
    end = text.find("<!-- /section: orchestrator-session-long -->")
    section = text[start:end] if start != -1 and end != -1 else ""

    assert "delegation" in section.lower(), (
        "orchestrator-session-long section must mention delegation"
    )


def test_orchestrator_session_long_contains_tracking_requirements() -> None:
    """The orchestrator-session-long section must include tracking requirements."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    start = text.find("<!-- section: orchestrator-session-long -->")
    end = text.find("<!-- /section: orchestrator-session-long -->")
    section = text[start:end] if start != -1 and end != -1 else ""

    assert "tracking" in section.lower() or "track" in section.lower(), (
        "orchestrator-session-long section must mention tracking"
    )


def test_orchestrator_session_long_contains_worktree_gates() -> None:
    """The orchestrator-session-long section must include worktree gates."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    start = text.find("<!-- section: orchestrator-session-long -->")
    end = text.find("<!-- /section: orchestrator-session-long -->")
    section = text[start:end] if start != -1 and end != -1 else ""

    assert "worktree" in section.lower(), (
        "orchestrator-session-long section must mention worktree"
    )


def test_start_bootstrap_is_minimal() -> None:
    """The start-bootstrap section must be minimal (for start prompts only)."""
    text = ORCHESTRATION_GATES_PATH.read_text(encoding="utf-8")

    start = text.find("<!-- section: start-bootstrap -->")
    end = text.find("<!-- /section: start-bootstrap -->")
    section = text[start:end] if start != -1 and end != -1 else ""

    # Bootstrap should be shorter than full orchestrator section (minimal)
    session_start = text.find("<!-- section: orchestrator-session-long -->")
    session_end = text.find("<!-- /section: orchestrator-session-long -->")
    session_section = text[session_start:session_end] if session_start != -1 and session_end != -1 else ""

    assert len(section) < len(session_section), (
        "start-bootstrap should be smaller than orchestrator-session-long (minimal for boot)"
    )
