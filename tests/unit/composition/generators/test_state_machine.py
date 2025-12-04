"""Tests for StateMachineGenerator.

Following strict TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor

Note: StateMachineGenerator now uses ComposableRegistry base class with:
- content_type: "generators"
- file_pattern: "STATE_MACHINE.md"
- get_context_vars(): Returns state machine data for {{#each}} expansion
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.generators import StateMachineGenerator


def test_state_machine_generator_exists():
    """Test that StateMachineGenerator class exists."""
    assert StateMachineGenerator is not None


def test_state_machine_generator_has_content_type():
    """Test that StateMachineGenerator has correct content_type."""
    generator = StateMachineGenerator()
    assert generator.content_type == "generators"


def test_state_machine_generator_has_file_pattern():
    """Test that StateMachineGenerator has correct file_pattern."""
    generator = StateMachineGenerator()
    assert generator.file_pattern == "STATE_MACHINE.md"


def test_state_machine_generator_get_context_vars_returns_dict(tmp_path: Path):
    """Test that get_context_vars returns a dictionary with expected keys."""
    generator = StateMachineGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("STATE_MACHINE", packs)

    assert isinstance(data, dict)
    assert "sources" in data
    assert "domains" in data
    assert "generated_at" in data


def test_state_machine_generator_get_context_vars_domains_is_list(tmp_path: Path):
    """Test that domains data is a list."""
    generator = StateMachineGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("STATE_MACHINE", packs)

    assert isinstance(data["domains"], list)


def test_state_machine_generator_compose_returns_markdown(tmp_path: Path):
    """Test that compose() returns markdown content."""
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

    # Create the generators template directory
    gen_dir = edison_dir / "generators"
    gen_dir.mkdir()
    (gen_dir / "STATE_MACHINE.md").write_text("""# State Machine
{{#each domains}}
## {{this.title}} Domain
{{#each this.states}}
- {{this.name}}
{{/each}}
{{/each}}
""")

    generator = StateMachineGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    content = generator.compose("STATE_MACHINE", packs)

    assert isinstance(content, str)
    assert "# State Machine" in content
    assert "Session" in content


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

    # Create the generators template directory
    gen_dir = edison_dir / "generators"
    gen_dir.mkdir()
    (gen_dir / "STATE_MACHINE.md").write_text("""# State Machine
{{#each domains}}
## {{this.title}} Domain
{{/each}}
""")

    generator = StateMachineGenerator(project_root=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result_path = generator.write(output_dir)

    assert result_path.exists()
    assert result_path == output_dir / "STATE_MACHINE.md"
    content = result_path.read_text()
    assert "# State Machine" in content
    assert "Session" in content
