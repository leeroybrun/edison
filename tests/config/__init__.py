"""Test configuration loaders.

This module provides centralized loading functions for all test configuration
files, ensuring NO hardcoded values in test code.

All config is loaded from YAML files in this directory:
- states.yaml: Task, QA, session states and status values
- paths.yaml: Directory structure and file patterns
- script_mappings.yaml: CLI command mappings
- env_vars.yaml: Environment variable definitions
- test_defaults.yaml: Default test values

Usage:
    from tests.config import load_states, load_script_mappings

    states = load_states()
    task_states = states['task']['states']

    mappings = load_script_mappings()
    domain, cmd = mappings['tasks/ready']
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from functools import lru_cache

_CONFIG_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_states() -> Dict[str, Any]:
    """Load state definitions from states.yaml.
    
    Returns:
        Dict with keys: task, qa, session, status
        Each containing state lists and metadata
    """
    config_path = _CONFIG_DIR / "states.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_paths() -> Dict[str, Any]:
    """Load path definitions from paths.yaml.
    
    Returns:
        Dict with keys: base_directories, subdirectories, file_patterns, git, config_files
    """
    config_path = _CONFIG_DIR / "paths.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_script_mappings() -> Dict[str, Tuple[str, Optional[str]]]:
    """Load script-to-CLI mappings from script_mappings.yaml.
    
    Returns:
        Dict mapping script name -> (domain, command)
        Example: "tasks/ready" -> ("task", "ready")
    """
    config_path = _CONFIG_DIR / "script_mappings.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Convert nested dict to flat tuples
    mappings = {}
    for script_name, mapping in data['mappings'].items():
        mappings[script_name] = (mapping['domain'], mapping['command'])
    
    return mappings


@lru_cache(maxsize=1)
def load_session_subcommands() -> Dict[str, str]:
    """Load session subcommand mappings from script_mappings.yaml.
    
    Returns:
        Dict mapping legacy subcommand -> new subcommand
        Example: "heartbeat" -> "track"
    """
    config_path = _CONFIG_DIR / "script_mappings.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return data['session_subcommands']


@lru_cache(maxsize=1)
def load_track_subcommands() -> List[str]:
    """Load valid track subcommands from script_mappings.yaml.
    
    Returns:
        List of valid subcommands for session track
    """
    config_path = _CONFIG_DIR / "script_mappings.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
    
    return data['track_subcommands']


@lru_cache(maxsize=1)
def load_env_vars() -> Dict[str, Any]:
    """Load environment variable definitions from env_vars.yaml.
    
    Returns:
        Dict with keys: primary, edison, git, test, fallbacks
    """
    config_path = _CONFIG_DIR / "env_vars.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_defaults() -> Dict[str, Any]:
    """Load default test values from test_defaults.yaml.

    Returns:
        Dict with default values for git, worktrees, timeouts, session, task, qa, etc.
    """
    config_path = _CONFIG_DIR / "test_defaults.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# Convenience accessors for common lookups

def get_task_states() -> List[str]:
    """Get list of all task state names."""
    states = load_states()
    return states['task']['unique_dirs']


def get_qa_states() -> List[str]:
    """Get list of all QA state names."""
    states = load_states()
    return states['qa']['unique_dirs']


def get_session_states() -> List[str]:
    """Get list of all session state names."""
    states = load_states()
    return states['session']['unique_dirs']


def get_state_directory(entity: str, state: str) -> str:
    """Get directory name for a given entity state.
    
    Args:
        entity: "task", "qa", or "session"
        state: State name (e.g., "wip", "done")
        
    Returns:
        Directory name for the state
    """
    states = load_states()
    return states[entity]['directories'][state]


def get_env_var_name(category: str, key: str) -> str:
    """Get environment variable name.
    
    Args:
        category: "primary", "edison", "git", or "test"
        key: Variable key (e.g., "agents_project_root")
        
    Returns:
        Environment variable name (e.g., "AGENTS_PROJECT_ROOT")
    """
    env_vars = load_env_vars()
    return env_vars[category][key]['name']


def get_default_value(section: str, key: str) -> Any:
    """Get default value from defaults.yaml.
    
    Args:
        section: Section name (e.g., "git", "session", "task")
        key: Key within section
        
    Returns:
        Default value
    """
    defaults = load_defaults()
    return defaults[section][key]


__all__ = [
    'load_states',
    'load_paths',
    'load_script_mappings',
    'load_session_subcommands',
    'load_track_subcommands',
    'load_env_vars',
    'load_defaults',
    'get_task_states',
    'get_qa_states',
    'get_session_states',
    'get_state_directory',
    'get_env_var_name',
    'get_default_value',
]
