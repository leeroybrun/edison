"""Tests for StateMachineGenerator.

Following strict TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.generators.state_machine import StateMachineGenerator


def test_state_machine_generator_exists():
    """Test that StateMachineGenerator class exists."""
    assert StateMachineGenerator is not None


def test_state_machine_generator_has_no_template():
    """Test that StateMachineGenerator has no template (renders directly from config)."""
    generator = StateMachineGenerator()
    assert generator.template_name is None


def test_state_machine_generator_has_output_filename():
    """Test that StateMachineGenerator has correct output_filename."""
    generator = StateMachineGenerator()
    assert generator.output_filename == "STATE_MACHINE.md"


def test_state_machine_generator_gather_data_returns_dict(tmp_path: Path):
    """Test that _gather_data returns a dictionary."""
    generator = StateMachineGenerator(project_root=tmp_path)
    data = generator._gather_data()

    assert isinstance(data, dict)
    assert "statemachine" in data


def test_state_machine_generator_generate_returns_markdown(tmp_path: Path):
    """Test that generate() returns markdown content."""
    # Create minimal state machine config
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    config_dir = edison_dir / "config"
    config_dir.mkdir()

    # Write minimal state machine config
    state_machine_config = config_dir / "state-machine.yaml"
    state_machine_config.write_text("""
statemachine:
  session:
    states:
      idle:
        description: "Idle state"
        initial: true
        allowed_transitions: []
      working:
        description: "Working state"
        final: true
        allowed_transitions: []
""")

    generator = StateMachineGenerator(project_root=tmp_path)
    content = generator.generate()

    assert isinstance(content, str)
    assert "# State Machine" in content
    assert "session" in content.lower()


def test_state_machine_generator_write_creates_file(tmp_path: Path):
    """Test that StateMachineGenerator.write() creates output file."""
    # Setup minimal project structure
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    config_dir = edison_dir / "config"
    config_dir.mkdir()

    # Write minimal state machine config
    state_machine_config = config_dir / "state-machine.yaml"
    state_machine_config.write_text("""
statemachine:
  session:
    states:
      idle:
        description: "Idle state"
        initial: true
        allowed_transitions: []
""")

    generator = StateMachineGenerator(project_root=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result_path = generator.write(output_dir)

    assert result_path.exists()
    assert result_path == output_dir / "STATE_MACHINE.md"
    content = result_path.read_text()
    assert "# State Machine" in content
    assert "session" in content.lower()
