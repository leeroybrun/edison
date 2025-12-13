"""Core condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from typing import Any, Mapping


def all_work_complete(ctx: Mapping[str, Any]) -> bool:
    """Check if all work is complete for the entity.
    
    Args:
        ctx: Context with 'session' or 'task' dict
        
    Returns:
        True if work is complete
    """
    # Check session
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        if session.get("work_complete") is not None:
            return bool(session.get("work_complete"))
    
    # Check task
    task = ctx.get("task", {})
    if isinstance(task, Mapping):
        if task.get("work_complete") is not None:
            return bool(task.get("work_complete"))
    
    # Default to True for lightweight CLI flows
    return True


def no_pending_commits(ctx: Mapping[str, Any]) -> bool:
    """Check if there are no pending commits.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if no pending commits
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        pending = session.get("pending_commits", 0)
        return int(pending or 0) == 0
    
    # Default to True
    return True


def ready_to_close(ctx: Mapping[str, Any]) -> bool:
    """Check if session is ready to close.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if ready to close
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        # Check explicit ready flag
        return bool(session.get("ready", True))
    
    # Default to True for flexibility
    return True
