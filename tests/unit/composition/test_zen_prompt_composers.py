#!/usr/bin/env python3
"""Tests for Zen prompt composition functions."""
from __future__ import annotations

import pytest
from pathlib import Path

import yaml

from edison.core.composition.composers import (
    compose_zen_prompt,
    compose_agent_zen_prompt,
    compose_validator_zen_prompt,
)
from edison.core.composition.agents import AgentRegistry
from edison.core.composition.validators import ValidatorRegistry
from edison.core.paths.project import get_project_config_dir


def _write_core_agent(project_dir: Path, name: str) -> Path:
    """Create a minimal core agent template."""
    core_agents_dir = project_dir / "core" / "agents"
    core_agents_dir.mkdir(parents=True, exist_ok=True)
    path = core_agents_dir / f"{name}.md"
    content = "\n".join(
        [
            "# Agent: {{AGENT_NAME}}",
            "",
            "## Role",
            f"Core role for {name}.",
            "",
            "## Tools",
            "{{TOOLS}}",
            "",
            "## Guidelines",
            "{{GUIDELINES}}",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path


def _write_validator_spec(project_dir: Path, validator_id: str, role: str) -> Path:
    """Create a minimal validator spec.
    
    With unified naming, the file is named after the role (e.g., 'global.md'),
    and multiple validator IDs (global-codex, global-claude, etc.) reference it.
    """
    validator_dir = project_dir / "core" / "validators" / "global"
    validator_dir.mkdir(parents=True, exist_ok=True)
    path = validator_dir / f"{role}.md"
    content = f"""# {validator_id} Validator

## Purpose
Validates {role} code quality.

## Checks
- Check 1
- Check 2
"""
    path.write_text(content, encoding="utf-8")
    return path


def _write_config(project_dir: Path, validators_roster: list = None) -> Path:
    """Write minimal config.yml with validator roster."""
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.yml"

    if validators_roster is None:
        validators_roster = []

    content = {
        "packs": {
            "active": [],
        },
        "validation": {
            "roster": {
                "global": validators_roster,
            }
        }
    }
    path.write_text(yaml.dump(content), encoding="utf-8")
    return path


def test_compose_agent_zen_prompt_contains_agent_content(isolated_project_env: Path) -> None:
    """Agent Zen prompts must contain agent-specific content, not validator content."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A known agent with core template
    agent_name = "api-builder"
    _write_core_agent(project_dir, agent_name)
    _write_config(project_dir)

    # When: Composing Zen prompt for the agent
    result = compose_agent_zen_prompt(agent_name, repo_root=root)

    # Then: Result should contain agent-specific markers
    assert "Agent" in result, "Zen prompt should contain 'Agent' marker"
    assert "api-builder" in result.lower() or "API Builder" in result, \
        "Zen prompt should reference the agent name"
    assert "constitutions/AGENTS.md" in result, \
        "Agent Zen prompt should reference AGENTS constitution"

    # And: Should NOT contain validator-specific content
    assert "Validator" not in result or "Agent" in result, \
        "Agent Zen prompt should not contain validator-only content"
    assert "constitutions/VALIDATORS.md" not in result, \
        "Agent Zen prompt should not reference VALIDATORS constitution"


def test_compose_validator_zen_prompt_contains_validator_content(isolated_project_env: Path) -> None:
    """Validator Zen prompts must contain validator-specific content, not agent content."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A known validator with spec
    # With unified naming: global-codex uses the 'global' role, so file is 'global.md'
    validator_name = "global-codex"
    _write_validator_spec(project_dir, validator_name, "global")  # role is 'global' not 'codex'
    _write_config(project_dir, validators_roster=[
        {"id": "global-codex", "name": "Codex Global Validator"}
    ])

    # When: Composing Zen prompt for the validator
    result = compose_validator_zen_prompt(validator_name, repo_root=root)

    # Then: Result should contain validator-specific markers
    assert "Validator" in result, "Zen prompt should contain 'Validator' marker"
    assert "global" in result.lower() or "Global" in result, \
        "Zen prompt should reference the validator name"
    assert "constitutions/VALIDATORS.md" in result, \
        "Validator Zen prompt should reference VALIDATORS constitution"

    # And: Should NOT contain agent-specific content
    assert "Agent:" not in result or "Validator" in result, \
        "Validator Zen prompt should not contain agent-only content"
    assert "constitutions/AGENTS.md" not in result, \
        "Validator Zen prompt should not reference AGENTS constitution"


def test_compose_zen_prompt_dispatches_to_agent(isolated_project_env: Path) -> None:
    """compose_zen_prompt should detect agents and call compose_agent_zen_prompt."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A known agent with core template
    agent_name = "api-builder"
    _write_core_agent(project_dir, agent_name)
    _write_config(project_dir)

    # When: Calling the dispatcher
    result = compose_zen_prompt(agent_name, repo_root=root)

    # Then: Result should be agent content
    assert "Agent" in result, "Should return agent content"
    assert "constitutions/AGENTS.md" in result, "Should reference AGENTS constitution"


def test_compose_zen_prompt_dispatches_to_validator(isolated_project_env: Path) -> None:
    """compose_zen_prompt should detect validators and call compose_validator_zen_prompt."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A known validator with spec
    # With unified naming: global-codex uses the 'global' role, so file is 'global.md'
    validator_name = "global-codex"
    _write_validator_spec(project_dir, validator_name, "global")  # role is 'global' not 'codex'
    _write_config(project_dir, validators_roster=[
        {"id": "global-codex", "name": "Codex Global Validator"}
    ])

    # When: Calling the dispatcher
    result = compose_zen_prompt(validator_name, repo_root=root)

    # Then: Result should be validator content
    assert "Validator" in result, "Should return validator content"
    assert "constitutions/VALIDATORS.md" in result, "Should reference VALIDATORS constitution"


def test_compose_zen_prompt_raises_for_unknown_name(isolated_project_env: Path) -> None:
    """compose_zen_prompt should raise ValueError for unknown names."""
    root = isolated_project_env
    
    # Given: An unknown name
    unknown_name = "this-does-not-exist"

    # When/Then: Should raise ValueError
    with pytest.raises(ValueError, match="Unknown agent or validator"):
        compose_zen_prompt(unknown_name, repo_root=root)


def test_agent_registry_has_exists_method(isolated_project_env: Path) -> None:
    """AgentRegistry must have an exists() method for role detection."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: An AgentRegistry with a known agent
    _write_core_agent(project_dir, "api-builder")
    registry = AgentRegistry(repo_root=root)

    # Then: Should have exists method
    assert hasattr(registry, "exists"), "AgentRegistry must have exists() method"
    assert callable(registry.exists), "exists() must be callable"

    # And: Should work for known agents
    assert registry.exists("api-builder") is True, "Should find existing agent"
    assert registry.exists("this-does-not-exist") is False, "Should not find non-existent agent"


def test_validator_registry_has_exists_method(isolated_project_env: Path) -> None:
    """ValidatorRegistry must have an exists() method for role detection."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A ValidatorRegistry with a known validator
    # With unified naming: global-codex uses the 'global' role, so file is 'global.md'
    _write_validator_spec(project_dir, "global-codex", "global")
    _write_config(project_dir, validators_roster=[
        {"id": "global-codex", "name": "Codex Global Validator"}
    ])
    registry = ValidatorRegistry(repo_root=root)

    # Then: Should have exists method
    assert hasattr(registry, "exists"), "ValidatorRegistry must have exists() method"
    assert callable(registry.exists), "exists() must be callable"

    # And: Should work for known validators
    assert registry.exists("global-codex") is True, "Should find existing validator"
    assert registry.exists("this-does-not-exist") is False, "Should not find non-existent validator"


def test_validator_registry_has_get_method(isolated_project_env: Path) -> None:
    """ValidatorRegistry must have a get() method to retrieve validator metadata."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: A ValidatorRegistry with a known validator
    # With unified naming: global-codex uses the 'global' role, so file is 'global.md'
    _write_validator_spec(project_dir, "global-codex", "global")
    _write_config(project_dir, validators_roster=[
        {"id": "global-codex", "name": "Codex Global Validator"}
    ])
    registry = ValidatorRegistry(repo_root=root)

    # Then: Should have get method
    assert hasattr(registry, "get"), "ValidatorRegistry must have get() method"
    assert callable(registry.get), "get() must be callable"

    # And: Should return metadata for known validators
    validator = registry.get("global-codex")
    assert isinstance(validator, dict), "get() should return a dict"
    assert "name" in validator or "id" in validator, "Should contain name or id"


def test_agent_registry_has_get_method(isolated_project_env: Path) -> None:
    """AgentRegistry must have a get() method to retrieve agent metadata."""
    root = isolated_project_env
    project_dir = get_project_config_dir(root, create=True)
    
    # Given: An AgentRegistry with a known agent
    _write_core_agent(project_dir, "api-builder")
    registry = AgentRegistry(repo_root=root)

    # Then: Should have get method
    assert hasattr(registry, "get"), "AgentRegistry must have get() method"
    assert callable(registry.get), "get() must be callable"

    # And: Should return metadata for known agents
    agent = registry.get("api-builder")
    assert isinstance(agent, dict), "get() should return a dict"
    assert "name" in agent, "Should contain name field"
