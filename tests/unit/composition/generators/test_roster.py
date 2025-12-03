"""Tests for roster generators (AgentRosterGenerator, ValidatorRosterGenerator).

Following strict TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.generators.roster import (
    AgentRosterGenerator,
    ValidatorRosterGenerator,
)


def test_agent_roster_generator_exists():
    """Test that AgentRosterGenerator class exists."""
    assert AgentRosterGenerator is not None


def test_agent_roster_generator_has_template_name():
    """Test that AgentRosterGenerator has correct template_name."""
    generator = AgentRosterGenerator()
    assert generator.template_name == "AVAILABLE_AGENTS"


def test_agent_roster_generator_has_output_filename():
    """Test that AgentRosterGenerator has correct output_filename."""
    generator = AgentRosterGenerator()
    assert generator.output_filename == "AVAILABLE_AGENTS.md"


def test_agent_roster_generator_gather_data_returns_dict(tmp_path: Path):
    """Test that _gather_data returns a dictionary with expected keys."""
    generator = AgentRosterGenerator(project_root=tmp_path)
    data = generator._gather_data()

    assert isinstance(data, dict)
    assert "agents" in data
    assert "timestamp" in data


def test_agent_roster_generator_gather_data_agents_is_list(tmp_path: Path):
    """Test that agents data is a list."""
    generator = AgentRosterGenerator(project_root=tmp_path)
    data = generator._gather_data()

    assert isinstance(data["agents"], list)


def test_validator_roster_generator_exists():
    """Test that ValidatorRosterGenerator class exists."""
    assert ValidatorRosterGenerator is not None


def test_validator_roster_generator_has_template_name():
    """Test that ValidatorRosterGenerator has correct template_name."""
    generator = ValidatorRosterGenerator()
    assert generator.template_name == "AVAILABLE_VALIDATORS"


def test_validator_roster_generator_has_output_filename():
    """Test that ValidatorRosterGenerator has correct output_filename."""
    generator = ValidatorRosterGenerator()
    assert generator.output_filename == "AVAILABLE_VALIDATORS.md"


def test_validator_roster_generator_gather_data_returns_dict(tmp_path: Path):
    """Test that _gather_data returns a dictionary with expected keys."""
    generator = ValidatorRosterGenerator(project_root=tmp_path)
    data = generator._gather_data()

    assert isinstance(data, dict)
    assert "global_validators" in data
    assert "critical_validators" in data
    assert "specialized_validators" in data
    assert "timestamp" in data


def test_validator_roster_generator_gather_data_validators_are_lists(tmp_path: Path):
    """Test that validator data values are lists."""
    generator = ValidatorRosterGenerator(project_root=tmp_path)
    data = generator._gather_data()

    assert isinstance(data["global_validators"], list)
    assert isinstance(data["critical_validators"], list)
    assert isinstance(data["specialized_validators"], list)


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
