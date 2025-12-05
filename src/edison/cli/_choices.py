"""Dynamic CLI choices from configuration.

Provides functions to dynamically populate argparse choices from workflow config.
This eliminates hardcoded state values in CLI argument definitions.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional


@lru_cache(maxsize=1)
def _get_workflow_config():
    """Get cached WorkflowConfig instance."""
    from edison.core.config.domains.workflow import WorkflowConfig
    return WorkflowConfig()


def get_state_choices(domain: str) -> List[str]:
    """Get valid states for a domain from config.
    
    Args:
        domain: "task", "qa", or "session"
        
    Returns:
        List of valid state names for the domain
    """
    return _get_workflow_config().get_states(domain)


def get_combined_state_choices() -> List[str]:
    """Get combined task + QA states for CLI that accepts both.
    
    Returns:
        Deduplicated list of all task and QA states
    """
    cfg = _get_workflow_config()
    return list(set(cfg.get_states("task") + cfg.get_states("qa")))


def get_semantic_state(domain: str, semantic: str) -> str:
    """Get configured state name for a semantic meaning.
    
    Args:
        domain: "task", "qa", or "session"
        semantic: Semantic state name (e.g., "wip", "done", "validated")
        
    Returns:
        The configured state name for that semantic meaning
    """
    return _get_workflow_config().get_semantic_state(domain, semantic)


def get_initial_state(domain: str) -> str:
    """Get the initial state for a domain.
    
    Args:
        domain: "task", "qa", or "session"
        
    Returns:
        The initial state name from config
    """
    return _get_workflow_config().get_initial_state(domain)


def get_final_state(domain: str) -> str:
    """Get the final state for a domain.
    
    Args:
        domain: "task", "qa", or "session"
        
    Returns:
        The final state name from config
    """
    return _get_workflow_config().get_final_state(domain)


__all__ = [
    "get_state_choices",
    "get_combined_state_choices",
    "get_semantic_state",
    "get_initial_state",
    "get_final_state",
]

