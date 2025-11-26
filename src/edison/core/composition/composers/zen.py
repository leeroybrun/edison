#!/usr/bin/env python3
from __future__ import annotations

"""Zen prompt composition for agents and validators."""

from pathlib import Path
from typing import Optional

from ..includes import ComposeError, _repo_root
from ..agents import AgentRegistry
from ..validators import ValidatorRegistry


def compose_agent_zen_prompt(agent_name: str, *, repo_root: Optional[Path] = None) -> str:
    """Compose Zen system prompt for an agent.

    Args:
        agent_name: Name of the agent to compose
        repo_root: Optional repository root path

    Returns:
        Formatted Zen prompt for the agent
    """
    from ..agents import compose_agent

    registry = AgentRegistry(repo_root=repo_root)
    agent = registry.get(agent_name)

    # Get full agent brief content
    # Load configuration to get active packs
    root = repo_root or _repo_root()
    from ...config import ConfigManager

    cfg_mgr = ConfigManager(root)
    try:
        config = cfg_mgr.load_config(validate=False)
    except FileNotFoundError:
        config = {}

    packs = ((config.get("packs", {}) or {}).get("active", []) or [])
    if not isinstance(packs, list):
        packs = []

    agent_content = compose_agent(agent_name, packs=packs, repo_root=root)

    return f"""# {agent['name']} Agent

{agent_content}

## Constitution Reference
Before starting work, read: constitutions/AGENTS.md
"""


def compose_validator_zen_prompt(validator_name: str, *, repo_root: Optional[Path] = None) -> str:
    """Compose Zen system prompt for a validator.

    Args:
        validator_name: Name of the validator to compose
        repo_root: Optional repository root path

    Returns:
        Formatted Zen prompt for the validator
    """
    # Import here to avoid circular dependency
    from .engine import CompositionEngine

    registry = ValidatorRegistry(repo_root=repo_root)
    validator = registry.get(validator_name)

    # Compose validator content using the engine
    root = repo_root or _repo_root()
    engine = CompositionEngine(repo_root=root)

    # Get validator composition
    results = engine.compose_validators(validator=validator_name, enforce_dry=False)

    if validator_name not in results:
        raise ComposeError(f"Failed to compose validator: {validator_name}")

    validator_result = results[validator_name]
    validator_content = validator_result.text

    validator_display_name = validator.get("name", validator_name)

    return f"""# {validator_display_name} Validator

{validator_content}

## Constitution Reference
Before starting validation, read: constitutions/VALIDATORS.md
"""


def compose_zen_prompt(name: str, *, repo_root: Optional[Path] = None) -> str:
    """Compose a Zen prompt for an agent or validator.

    Determines role type from registry and calls appropriate composer.

    Args:
        name: Name of the agent or validator
        repo_root: Optional repository root path

    Returns:
        Formatted Zen prompt for the role

    Raises:
        ValueError: If name is not found in either registry
    """
    root = repo_root or _repo_root()

    # Check if it's a validator
    validator_registry = ValidatorRegistry(repo_root=root)
    if validator_registry.exists(name):
        return compose_validator_zen_prompt(name, repo_root=root)

    # Check if it's an agent
    agent_registry = AgentRegistry(repo_root=root)
    if agent_registry.exists(name):
        return compose_agent_zen_prompt(name, repo_root=root)

    raise ValueError(f"Unknown agent or validator: {name}")


__all__ = [
    "compose_zen_prompt",
    "compose_agent_zen_prompt",
    "compose_validator_zen_prompt",
]
