"""Centralized config loading utilities.

This module provides utilities for loading specific config sections and
resolving semantic states from the unified configuration system.

Usage:
    from edison.core.utils.config import load_config_section, get_states_for_domain

    # Load a specific config section
    statemachine = load_config_section("statemachine")

    # Get states for a domain
    task_states = get_states_for_domain("task")
    qa_states = get_states_for_domain("qa")

    # Get semantic states
    initial = get_initial_state("task")
    active = get_active_state("qa")
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.config.cache import get_cached_config


@lru_cache(maxsize=8)
def _load_config_section_impl(
    section_name: str,
    repo_root_str: str,
    required: bool = True
) -> Dict[str, Any]:
    """Internal implementation with string-based caching.

    Args:
        section_name: Config section to load (e.g., "statemachine", "tasks", "qa")
        repo_root_str: Project root path as string (empty for auto-detect)
        required: If True, raise KeyError if section missing

    Returns:
        Config section dict, or empty dict if not required and missing

    Raises:
        KeyError: If section is required but missing
    """
    repo_root = Path(repo_root_str) if repo_root_str else None
    config = get_cached_config(repo_root=repo_root)

    if section_name not in config:
        if required:
            raise KeyError(f"Config section '{section_name}' not found")
        return {}

    return config.get(section_name, {})


def load_config_section(
    section_name: str,
    repo_root: Optional[Path] = None,
    required: bool = True
) -> Dict[str, Any]:
    """Load a specific section from config.

    Args:
        section_name: Config section to load (e.g., "statemachine", "tasks", "qa")
        repo_root: Project root path (auto-detected if None)
        required: If True, raise KeyError if section missing

    Returns:
        Config section dict, or empty dict if not required and missing

    Raises:
        KeyError: If section is required but missing

    Example:
        >>> statemachine = load_config_section("statemachine")
        >>> workflow = load_config_section("workflow")
    """
    return _load_config_section_impl(section_name, str(repo_root) if repo_root else "", required)


@lru_cache(maxsize=8)
def _get_states_for_domain_impl(domain: str, repo_root_str: str) -> List[str]:
    """Internal implementation with string-based caching.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root_str: Project root path as string (empty for auto-detect)

    Returns:
        List of state names from config

    Raises:
        ValueError: If domain config is invalid or missing
    """
    repo_root = Path(repo_root_str) if repo_root_str else None
    statemachine = load_config_section("statemachine", repo_root=repo_root)

    domain_cfg = statemachine.get(domain)
    if not isinstance(domain_cfg, dict):
        raise ValueError(f"state-machine config missing '{domain}' domain definition")

    states_cfg = domain_cfg.get("states")
    if isinstance(states_cfg, dict):
        return list(states_cfg.keys())
    if isinstance(states_cfg, list):
        return [str(s) for s in states_cfg]

    raise ValueError(f"statemachine.{domain}.states must be a dict or list")


def get_states_for_domain(domain: str, repo_root: Optional[Path] = None) -> List[str]:
    """Get allowed states for a domain from config.

    Loads states from the state-machine.yaml config file.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root: Project root path (auto-detected if None)

    Returns:
        List of state names from config

    Raises:
        ValueError: If domain config is invalid or missing

    Example:
        >>> task_states = get_states_for_domain("task")
        >>> ["todo", "wip", "done", "validated"]
    """
    return _get_states_for_domain_impl(domain, str(repo_root) if repo_root else "")


def _find_initial_state(domain: str, repo_root: Optional[Path] = None) -> str:
    """Find the initial state for a domain from config metadata."""
    statemachine = load_config_section("statemachine", repo_root=repo_root)
    domain_cfg = statemachine.get(domain, {})
    states_cfg = domain_cfg.get("states", {})

    # Look for state marked as initial=true
    if isinstance(states_cfg, dict):
        for state_name, state_meta in states_cfg.items():
            if isinstance(state_meta, dict) and state_meta.get("initial"):
                return state_name

    # Fallback: first state in list
    states = get_states_for_domain(domain, repo_root=repo_root)
    return states[0] if states else "todo"


def get_initial_state(domain: str, repo_root: Optional[Path] = None) -> str:
    """Get initial/default state for a domain.

    Returns the state marked with initial=true in the config,
    or the first state in the list as fallback.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root: Project root path (auto-detected if None)

    Returns:
        Initial state name

    Example:
        >>> get_initial_state("task")
        'todo'
        >>> get_initial_state("qa")
        'waiting'
    """
    return _find_initial_state(domain, repo_root=repo_root)


def get_active_state(domain: str, repo_root: Optional[Path] = None) -> str:
    """Get active/in-progress state for a domain.

    Returns 'wip' (work in progress) for both task and qa domains.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root: Project root path (auto-detected if None)

    Returns:
        Active state name (typically "wip")

    Example:
        >>> get_active_state("task")
        'wip'
    """
    # Both domains use 'wip' as active state
    return "wip"


def get_completed_state(domain: str, repo_root: Optional[Path] = None) -> str:
    """Get completion state for a domain.

    Returns 'done' for both task and qa domains.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root: Project root path (auto-detected if None)

    Returns:
        Completion state name (typically "done")

    Example:
        >>> get_completed_state("task")
        'done'
    """
    # Both domains use 'done' as completion state
    return "done"


def get_final_state(domain: str, repo_root: Optional[Path] = None) -> str:
    """Get final/validated state for a domain.

    Returns the state marked with final=true in the config,
    or 'validated' as fallback.

    Args:
        domain: Domain name ("task" or "qa")
        repo_root: Project root path (auto-detected if None)

    Returns:
        Final state name (typically "validated")

    Example:
        >>> get_final_state("task")
        'validated'
    """
    statemachine = load_config_section("statemachine", repo_root=repo_root)
    domain_cfg = statemachine.get(domain, {})
    states_cfg = domain_cfg.get("states", {})

    # Look for state marked as final=true
    if isinstance(states_cfg, dict):
        for state_name, state_meta in states_cfg.items():
            if isinstance(state_meta, dict) and state_meta.get("final"):
                return state_name

    # Fallback
    return "validated"


def get_semantic_state(domain: str, semantic_key: str, repo_root: Optional[Path] = None) -> str:
    """Resolve a semantic state to the configured state name.

    Uses the workflow validation lifecycle configuration to map semantic
    keys like 'validated', 'done', 'wip' to actual state names.

    Args:
        domain: Domain name ("task" or "qa")
        semantic_key: Semantic state identifier (e.g., "validated", "done", "wip", "todo")
        repo_root: Project root path (auto-detected if None)

    Returns:
        Resolved state name, or the semantic_key itself if not mapped

    Example:
        >>> get_semantic_state("task", "validated")
        'validated'
        >>> get_semantic_state("qa", "waiting")
        'waiting'
    """
    # validationLifecycle is a top-level key in the merged config
    lc = load_config_section("validationLifecycle", repo_root=repo_root, required=False)
    if not lc:
        # No lifecycle config, return key as-is
        return semantic_key
    on_approve = lc.get("onApprove", {})
    on_reject = lc.get("onReject", {})
    on_revalidate = lc.get("onRevalidate", {})

    def _parse_target(transition: str) -> str:
        """Parse target state from 'source → target' transition string."""
        if not transition or "→" not in transition:
            return ""
        return transition.split("→")[1].strip()

    def _parse_source(transition: str) -> str:
        """Parse source state from 'source → target' transition string."""
        if not transition or "→" not in transition:
            return ""
        return transition.split("→")[0].strip()

    if domain == "task":
        if semantic_key == "validated":
            return _parse_target(on_approve.get("taskState", "")) or "validated"
        if semantic_key == "done":
            return _parse_source(on_approve.get("taskState", "")) or "done"
        if semantic_key == "wip":
            return _parse_target(on_reject.get("taskState", "")) or "wip"
        if semantic_key == "todo":
            return get_initial_state(domain, repo_root=repo_root)

    if domain == "qa":
        if semantic_key == "validated":
            return _parse_target(on_approve.get("qaState", "")) or "validated"
        if semantic_key == "done":
            return _parse_source(on_approve.get("qaState", "")) or "done"
        if semantic_key == "wip":
            return _parse_source(on_reject.get("qaState", "")) or "wip"
        if semantic_key == "waiting":
            return _parse_target(on_reject.get("qaState", "")) or "waiting"
        if semantic_key == "todo":
            return _parse_target(on_revalidate.get("qaState", "")) or "todo"

    # No mapping found, return the key itself
    return semantic_key


__all__ = [
    "load_config_section",
    "get_states_for_domain",
    "get_initial_state",
    "get_active_state",
    "get_completed_state",
    "get_final_state",
    "get_semantic_state",
]
