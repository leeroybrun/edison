"""Core guard functions for state machine transitions.

These guards are available across all domains and provide
fundamental transition control.
"""
from __future__ import annotations

from typing import Any, Mapping


def always_allow(ctx: Mapping[str, Any]) -> bool:
    """Explicit opt-in to allow any transition.
    
    Use this guard when a transition should always be allowed,
    regardless of context. This is useful for manual overrides
    or transitions that have no prerequisites.
    
    Args:
        ctx: Context dict (ignored)
        
    Returns:
        Always True
    """
    return True


def fail_closed(ctx: Mapping[str, Any]) -> bool:
    """Explicit fail-closed guard that always blocks.
    
    Use this guard when a transition should be blocked by default
    until specific conditions are met through other mechanisms.
    
    Args:
        ctx: Context dict (ignored)
        
    Returns:
        Always False
    """
    return False


