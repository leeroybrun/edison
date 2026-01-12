"""Tests for roster generators (AgentRosterGenerator, ValidatorRosterGenerator).

Following strict TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor

Note: Generators now use ComposableRegistry base class with:
- content_type: "generators"
- file_pattern: The template filename
- get_context_vars(): Returns data for {{#each}} expansion
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.generators import (
    AgentRosterGenerator,
    ValidatorRosterGenerator,
)


def test_agent_roster_generator_exists():
    """Test that AgentRosterGenerator class exists."""
    assert AgentRosterGenerator is not None


def test_agent_roster_generator_has_content_type():
    """Test that AgentRosterGenerator has correct content_type."""
    generator = AgentRosterGenerator()
    assert generator.content_type == "generators"


def test_agent_roster_generator_has_file_pattern():
    """Test that AgentRosterGenerator has correct file_pattern."""
    generator = AgentRosterGenerator()
    assert generator.file_pattern == "AVAILABLE_AGENTS.md"


def test_agent_roster_generator_get_context_vars_returns_dict(tmp_path: Path):
    """Test that get_context_vars returns a dictionary with expected keys."""
    generator = AgentRosterGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("AVAILABLE_AGENTS", packs)

    assert isinstance(data, dict)
    assert "agents" in data
    assert "generated_at" in data


def test_agent_roster_generator_get_context_vars_agents_is_list(tmp_path: Path):
    """Test that agents data is a list."""
    generator = AgentRosterGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("AVAILABLE_AGENTS", packs)

    assert isinstance(data["agents"], list)


def test_validator_roster_generator_exists():
    """Test that ValidatorRosterGenerator class exists."""
    assert ValidatorRosterGenerator is not None


def test_validator_roster_generator_has_content_type():
    """Test that ValidatorRosterGenerator has correct content_type."""
    generator = ValidatorRosterGenerator()
    assert generator.content_type == "generators"


def test_validator_roster_generator_has_file_pattern():
    """Test that ValidatorRosterGenerator has correct file_pattern."""
    generator = ValidatorRosterGenerator()
    assert generator.file_pattern == "AVAILABLE_VALIDATORS.md"


def test_validator_roster_generator_get_context_vars_returns_dict(tmp_path: Path):
    """Test that get_context_vars returns a dictionary with expected keys."""
    generator = ValidatorRosterGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("AVAILABLE_VALIDATORS", packs)

    assert isinstance(data, dict)
    assert "waves" in data
    assert "validators_by_wave" in data
    assert "all_validators" in data
    assert "generated_at" in data


def test_validator_roster_generator_get_context_vars_validators_are_lists(tmp_path: Path):
    """Test that validator data values are lists."""
    generator = ValidatorRosterGenerator(project_root=tmp_path)
    packs = generator.get_active_packs()
    data = generator.get_context_vars("AVAILABLE_VALIDATORS", packs)

    assert isinstance(data["waves"], list)
    assert isinstance(data["all_validators"], list)
    # Each wave gets a <wave>_validators list accessor.
    for wave in data.get("wave_names", []) or []:
        assert isinstance(data.get(f"{wave}_validators"), list)


def test_agent_roster_generator_write_creates_file(tmp_path: Path):
    """Test that AgentRosterGenerator.write() creates output file."""
    # Setup minimal project structure
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    agents_dir = edison_dir / "agents"
    agents_dir.mkdir()

    generator = AgentRosterGenerator(project_root=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result_path = generator.write(output_dir)

    assert result_path.exists()
    assert result_path == output_dir / "AVAILABLE_AGENTS.md"
    content = result_path.read_text()
    assert "# Available Agents" in content


def test_validator_roster_generator_write_creates_file(tmp_path: Path):
    """Test that ValidatorRosterGenerator.write() creates output file."""
    # Setup minimal project structure
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()

    generator = ValidatorRosterGenerator(project_root=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result_path = generator.write(output_dir)

    assert result_path.exists()
    assert result_path == output_dir / "AVAILABLE_VALIDATORS.md"
    content = result_path.read_text()
    assert "# Available Validators" in content
    # Critical: roster output must not contain unresolved loop placeholders.
    assert "{{this.id}}" not in content
    assert "{{this.engine}}" not in content
    assert "{{this.prompt}}" not in content
