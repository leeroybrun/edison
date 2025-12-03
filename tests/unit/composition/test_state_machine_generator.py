"""Tests for StateMachineGenerator.

Tests the unified generator for STATE_MACHINE.md documentation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.generators.state_machine import StateMachineGenerator


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_state_machine_generator_instantiation(isolated_project_env: Path) -> None:
    """StateMachineGenerator can be instantiated."""
    generator = StateMachineGenerator(project_root=isolated_project_env)
    assert generator is not None
    assert generator.project_root == isolated_project_env


def test_state_machine_doc_written_to_generated_dir(isolated_project_env: Path) -> None:
    """State machine doc should be written to the specified output path."""
    repo_root = isolated_project_env
    output_dir = repo_root / ".edison" / "_generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = StateMachineGenerator(project_root=repo_root)
    output_path = generator.write(output_dir)

    assert output_path.exists(), "STATE_MACHINE.md must be written to .edison/_generated"
    content = _read_file(output_path)
    assert "AUTO-GENERATED FILE" in content or "State Machine" in content
    # Should contain some state machine content
    assert "state" in content.lower() or "transition" in content.lower()


def test_state_machine_doc_contains_expected_sections(isolated_project_env: Path) -> None:
    """State machine doc should contain key sections."""
    repo_root = isolated_project_env
    output_dir = repo_root / ".edison" / "_generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = StateMachineGenerator(project_root=repo_root)
    output_path = generator.write(output_dir)

    content = _read_file(output_path)
    # Should have task/QA/session domain coverage
    assert any(word in content.lower() for word in ["task", "qa", "session"])
