"""Session-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""
from __future__ import annotations

from typing import Any, Mapping


def can_activate_session(ctx: Mapping[str, Any]) -> bool:
    """Session can activate if it has at least one claimed task.
    
    FAIL-CLOSED: Returns False if session data is missing.
    
    Prerequisites:
    - Session must exist in context
    - If tasks are present, at least one must be claimed
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session can be activated
    """
    session = ctx.get("session")
    if not isinstance(session, Mapping):
        return False  # FAIL-CLOSED
    
    # Get task count
    task_count = session.get("task_count")
    if task_count is None:
        tasks = session.get("tasks")
        if isinstance(tasks, Mapping):
            task_count = len(tasks)
        elif isinstance(tasks, list):
            task_count = len(tasks)
        else:
            task_count = 0
    
    # Empty session can activate (tasks will be claimed later)
    if task_count == 0:
        return True
    
    # With tasks, at least one must be claimed
    claimed = session.get("claimed", False)
    return bool(claimed)


def can_complete_session(ctx: Mapping[str, Any]) -> bool:
    """Session can complete if all work is done and ready.
    
    FAIL-CLOSED: Returns False if session data is missing.
    
    Prerequisites:
    - Session must exist in context
    - Session must be marked as ready to complete
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session is ready to complete
    """
    session = ctx.get("session")
    if not isinstance(session, Mapping):
        return False  # FAIL-CLOSED
    
    # Check explicit ready flag
    ready = session.get("ready_to_complete")
    if ready is not None:
        return bool(ready)
    
    # Also check 'ready' flag as alternative
    return bool(session.get("ready", False))


def has_session_blockers(ctx: Mapping[str, Any]) -> bool:
    """Check if session has blockers preventing progress.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session has blockers
    """
    session = ctx.get("session")
    if not isinstance(session, Mapping):
        return False
    
    return bool(session.get("blocked") or session.get("blockers"))


def is_session_ready(ctx: Mapping[str, Any]) -> bool:
    """Check if session is ready for closing/validation.
    
    FAIL-CLOSED: Returns False if session data is missing.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session is ready
    """
    session = ctx.get("session")
    if not isinstance(session, Mapping):
        return False  # FAIL-CLOSED
    
    return bool(session.get("ready", False))


