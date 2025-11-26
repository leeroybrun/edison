from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.output.state_machine import generate_state_machine_doc as write_state_machine_docs


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_state_machine_doc_written_to_generated_dir(isolated_project_env: Path) -> None:
    """State machine doc should be written to the specified output path."""
    repo_root = isolated_project_env
    output_path = repo_root / ".edison" / "_generated" / "STATE_MACHINE.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_state_machine_docs(output_path)

    assert output_path.exists(), "STATE_MACHINE.md must be written to .edison/_generated"
    content = _read(output_path)
    assert "AUTO-GENERATED FILE" in content or "State Machine" in content
    # Should contain some state machine content
    assert "state" in content.lower() or "transition" in content.lower()


def test_state_machine_doc_contains_expected_sections(isolated_project_env: Path) -> None:
    """State machine doc should contain key sections."""
    repo_root = isolated_project_env
    output_path = repo_root / ".edison" / "_generated" / "STATE_MACHINE.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_state_machine_docs(output_path)

    content = _read(output_path)
    # Should have task/QA/session domain coverage
    assert any(word in content.lower() for word in ["task", "qa", "session"])
