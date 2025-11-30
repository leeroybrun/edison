"""I/O utilities for writing test files.

This module provides centralized I/O utilities for test helpers, ensuring
consistent file operations across the test suite.

All functions create parent directories automatically if they don't exist.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def write_yaml(
    path: Path,
    data: Any,
    *,
    sort_keys: bool = True,
    default_flow_style: bool = False,
) -> None:
    """Write data to YAML file, creating parent directories if needed.

    Args:
        path: Target file path
        data: Data to serialize as YAML
        sort_keys: Sort dictionary keys in output (default: True)
        default_flow_style: Use flow style for collections (default: False)

    Examples:
        >>> write_yaml(Path("config.yml"), {"key": "value"})
        >>> write_yaml(Path("data/nested.yml"), {"a": 1, "b": 2}, sort_keys=False)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = yaml.safe_dump(
        data,
        default_flow_style=default_flow_style,
        sort_keys=sort_keys,
        allow_unicode=True,
    )
    path.write_text(content, encoding="utf-8")


def write_json(
    path: Path,
    data: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> None:
    """Write data to JSON file, creating parent directories if needed.

    Args:
        path: Target file path
        data: Data to serialize as JSON
        indent: Indentation level (default: 2)
        sort_keys: Sort dictionary keys in output (default: True)
        ensure_ascii: Escape non-ASCII characters (default: False)

    Examples:
        >>> write_json(Path("data.json"), {"key": "value"})
        >>> write_json(Path("output/result.json"), data, indent=4)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(
        data,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=ensure_ascii,
    )
    path.write_text(content, encoding="utf-8")


def write_config(
    base_path: Path,
    content: str = "",
    *,
    filename: str = "config.yml",
) -> Path:
    """Write config content to .edison/config/ directory.

    Creates .edison/config/ directory structure and writes the config file.
    If no content is provided, creates an empty config file.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        content: Configuration file content (default: empty string)
        filename: Config filename (default: "config.yml")

    Returns:
        Path: Path to the created config file

    Examples:
        >>> config_path = write_config(tmp_path, "test: value\\n")
        >>> assert config_path == tmp_path / ".edison" / "config" / "config.yml"
        >>> # Create empty config
        >>> config_path = write_config(tmp_path)
    """
    base_path = Path(base_path)
    config_dir = base_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / filename
    config_path.write_text(content, encoding="utf-8")

    return config_path


def write_text(path: Path, content: str) -> None:
    """Write text content to file, creating parent directories if needed.

    Args:
        path: Target file path
        content: Text content to write

    Examples:
        >>> write_text(Path("output.txt"), "Hello, World!\\n")
        >>> write_text(Path("deep/nested/file.txt"), content)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_guideline(path: Path, content: str) -> None:
    """Write guideline/documentation content to file.

    This is a specialized version of write_text for writing guideline
    and documentation files (typically Markdown).

    Args:
        path: Target file path
        content: Guideline content to write

    Examples:
        >>> write_guideline(Path("GUIDE.md"), "# Guide\\n\\nContent\\n")
    """
    write_text(path, content)


def format_round_dir(round_num: int, *, pattern: str = "round-{num}") -> str:
    """Format a round directory name.

    Args:
        round_num: Round number
        pattern: Format pattern with {num} placeholder (default: "round-{num}")

    Returns:
        str: Formatted round directory name

    Examples:
        >>> format_round_dir(1)
        'round-1'
        >>> format_round_dir(5, pattern="iteration-{num}")
        'iteration-5'
    """
    return pattern.format(num=round_num)


def create_round_dir(
    base_path: Path,
    round_num: int,
    *,
    pattern: str = "round-{num}",
) -> Path:
    """Create a round directory under base_path.

    Args:
        base_path: Base directory path
        round_num: Round number
        pattern: Format pattern with {num} placeholder (default: "round-{num}")

    Returns:
        Path: Path to the created round directory

    Examples:
        >>> round_dir = create_round_dir(tmp_path, 1)
        >>> assert round_dir == tmp_path / "round-1"
        >>> assert round_dir.exists()
    """
    base_path = Path(base_path)
    round_dir_name = format_round_dir(round_num, pattern=pattern)
    round_dir = base_path / round_dir_name
    round_dir.mkdir(parents=True, exist_ok=True)
    return round_dir


def write_generated_agent(
    base_path: Path,
    agent_name: str,
    *,
    role_text: str = None,
    base_dir: str = ".edison",
) -> Path:
    """Write generated agent file to _generated/agents/ directory.

    Creates a standardized agent markdown file with sections for role, tools,
    guidelines, and workflows.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        agent_name: Name of the agent (e.g., "api-builder")
        role_text: Custom role text (default: generated from agent_name)
        base_dir: Base directory name (default: ".edison", can be ".agents")

    Returns:
        Path: Path to the created agent file

    Examples:
        >>> path = write_generated_agent(tmp_path, "api-builder")
        >>> assert path == tmp_path / ".edison" / "_generated" / "agents" / "api-builder.md"
    """
    base_path = Path(base_path)
    agents_dir = base_path / base_dir / "_generated" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_path = agents_dir / f"{agent_name}.md"

    # Generate default role text if not provided
    if role_text is None:
        role_text = f"Specialized agent for {agent_name} tasks."

    # Create standardized agent file content
    content = f"""# Agent: {agent_name}

## Role

{role_text}

## Tools

- File operations
- Code generation
- Testing utilities

## Guidelines

- Follow project conventions
- Write clean, maintainable code
- Include comprehensive tests

## Workflows

1. Analyze requirements
2. Design solution
3. Implement changes
4. Validate results
"""

    agent_path.write_text(content, encoding="utf-8")
    return agent_path


def write_orchestrator_manifest(
    base_path: Path,
    *,
    agents: dict = None,
    base_dir: str = ".edison",
) -> Path:
    """Write orchestrator manifest JSON to _generated/ directory.

    Creates a manifest file with composition metadata, agent roster, and validators.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        agents: Custom agent roster dict (default: minimal roster)
        base_dir: Base directory name (default: ".edison", can be ".agents")

    Returns:
        Path: Path to the created manifest file

    Examples:
        >>> path = write_orchestrator_manifest(tmp_path)
        >>> assert path == tmp_path / ".edison" / "_generated" / "orchestrator-manifest.json"
    """
    base_path = Path(base_path)
    generated_dir = base_path / base_dir / "_generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = generated_dir / "orchestrator-manifest.json"

    # Use default agents if not provided
    if agents is None:
        agents = {
            "generic": [],
            "specialized": [],
            "project": []
        }

    # Calculate total agent count
    total_agents = sum(len(v) for v in agents.values())

    # Create manifest structure
    manifest_data = {
        "version": "1.0.0",
        "generated": True,
        "composition": {
            "agentsCount": total_agents,
            "validatorsCount": 0,
        },
        "validators": [],
        "agents": agents,
    }

    write_json(manifest_path, manifest_data)
    return manifest_path


def write_orchestrator_constitution(
    base_path: Path,
    *,
    content: str = None,
    base_dir: str = ".edison",
) -> Path:
    """Write orchestrator constitution to _generated/constitutions/ directory.

    Creates a constitution markdown file with orchestrator governance rules.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        content: Custom constitution content (default: minimal constitution)
        base_dir: Base directory name (default: ".edison", can be ".agents")

    Returns:
        Path: Path to the created constitution file

    Examples:
        >>> path = write_orchestrator_constitution(tmp_path)
        >>> assert path == tmp_path / ".edison" / "_generated" / "constitutions" / "ORCHESTRATORS.md"
    """
    base_path = Path(base_path)
    constitutions_dir = base_path / base_dir / "_generated" / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)

    constitution_path = constitutions_dir / "ORCHESTRATORS.md"

    # Use default content if not provided
    if content is None:
        content = """# Test Orchestrator Constitution

## Purpose

This constitution defines the governance and operational principles for orchestrators.

## Principles

1. Maintain separation of concerns
2. Ensure clear delegation paths
3. Validate all outputs
4. Document all decisions

## Responsibilities

- Coordinate agent activities
- Enforce quality standards
- Manage task distribution
- Report status and progress
"""

    constitution_path.write_text(content, encoding="utf-8")
    return constitution_path


def write_minimal_compose_config(
    base_path: Path,
    *,
    platforms: list = None,
    include_hook_type: bool = False,
    include_env: bool = False,
) -> Path:
    """Write minimal compose configuration for testing.

    Creates the necessary directory structure and config files for
    compose commands to work in tests.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        platforms: List of platforms to enable (default: ["claude"])
        include_hook_type: Include hook type definitions
        include_env: Include environment variables in config

    Returns:
        Path: Path to the created config directory

    Examples:
        >>> write_minimal_compose_config(tmp_path)
        >>> write_minimal_compose_config(tmp_path, platforms=["claude", "cursor"])
    """
    base_path = Path(base_path)
    if platforms is None:
        platforms = ["claude"]

    # Create .edison/core/config directory
    config_dir = base_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create commands.yaml with a demo command
    commands_data = {
        "commands": {
            "definitions": [
                {
                    "id": "demo-cmd",
                    "domain": "demo",
                    "command": "demo",
                    "short_desc": "Demo command for testing",
                    "full_desc": "A demo command used in tests.",
                    "cli": "echo demo",
                    "args": [],
                    "when_to_use": "For testing compose functionality",
                    "related_commands": [],
                }
            ],
            "selection": {"mode": "all"},
        }
    }
    write_yaml(config_dir / "commands.yaml", commands_data)

    # Create settings.yaml with permissions
    settings_data = {
        "settings": {
            "permissions": {
                "allow": ["Read(./**)"],
            }
        }
    }
    write_yaml(config_dir / "settings.yaml", settings_data)

    # Create main config.yml
    main_config = {
        "composition": {
            "platforms": platforms,
        }
    }
    if include_env:
        main_config["env"] = {"TEST_VAR": "test_value"}

    write_yaml(config_dir / "config.yml", main_config)

    if include_hook_type:
        hooks_data = {
            "hooks": {
                "definitions": [
                    {
                        "id": "demo-hook",
                        "type": "pre-commit",
                        "script": "echo hook",
                    }
                ]
            }
        }
        write_yaml(config_dir / "hooks.yaml", hooks_data)

    return config_dir


def write_db_config(
    base_path: Path,
    *,
    project: str = "test",
) -> Path:
    """Write database configuration for testing.

    Creates the necessary config for session database operations.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        project: Project name for database naming

    Returns:
        Path: Path to the created config file
    """
    base_path = Path(base_path)
    config_dir = base_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_data = {
        "project": {
            "name": project,
        },
        "database": {
            "enabled": True,
            "prefix": project,
        },
    }
    config_path = config_dir / "config.yml"
    write_yaml(config_path, config_data)
    return config_path


def write_orchestrator_config(
    base_path: Path,
    profiles: dict,
    *,
    default: str = "default",
    core_config: bool = False,
) -> Path:
    """Write orchestrator configuration for testing.

    Creates orchestrator profile configuration.

    Args:
        base_path: Base directory (typically tmp_path in tests)
        profiles: Dictionary of profile name to profile configuration
        default: Default profile name
        core_config: If True, write to .edison/core/config instead of .edison/config

    Returns:
        Path: Path to the created config file
    """
    base_path = Path(base_path)
    if core_config:
        config_dir = base_path / ".edison" / "core" / "config"
    else:
        config_dir = base_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_data = {
        "orchestrator": {
            "profiles": profiles,
            "default": default,
        },
    }
    config_path = config_dir / "orchestrator.yml"
    write_yaml(config_path, config_data)
    return config_path


# Alias for backward compatibility with test imports
_write_minimal_compose_config = write_minimal_compose_config


__all__ = [
    "write_yaml",
    "write_json",
    "write_config",
    "write_text",
    "write_guideline",
    "format_round_dir",
    "create_round_dir",
    "write_generated_agent",
    "write_orchestrator_manifest",
    "write_orchestrator_constitution",
    "write_minimal_compose_config",
    "write_db_config",
    "write_orchestrator_config",
]
