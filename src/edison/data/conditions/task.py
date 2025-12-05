"""Task-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from typing import Any, Mapping


def has_task(ctx: Mapping[str, Any]) -> bool:
    """Check if session has at least one task.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session has tasks
    """
    session = ctx.get("session", {})
    if not isinstance(session, Mapping):
        return True  # Allow if no session context
    
    # Check task count
    task_count = session.get("task_count")
    if task_count is not None:
        return int(task_count) > 0
    
    # Check tasks directly
    tasks = session.get("tasks")
    if isinstance(tasks, Mapping):
        return len(tasks) > 0
    if isinstance(tasks, list):
        return len(tasks) > 0
    
    # Empty session is allowed to activate (tasks claimed later)
    return True


def task_claimed(ctx: Mapping[str, Any]) -> bool:
    """Check if task is claimed by the session.
    
    Args:
        ctx: Context with 'session' or 'task' dict
        
    Returns:
        True if task is claimed
    """
    # Check session's claimed flag
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        claimed = session.get("claimed")
        if claimed is not None:
            return bool(claimed)
    
    # Check task's session_id
    task = ctx.get("task", {})
    if isinstance(task, Mapping):
        task_session = task.get("session_id") or task.get("sessionId")
        return bool(task_session)
    
    # Default to True for flexibility
    return True


def task_ready_for_qa(ctx: Mapping[str, Any]) -> bool:
    """Check if task is ready for QA validation.
    
    Args:
        ctx: Context with 'task' dict
        
    Returns:
        True if task is ready for QA
    """
    task = ctx.get("task", {})
    if not isinstance(task, Mapping):
        return False
    
    # Check ready flag
    ready = task.get("ready_for_qa") or task.get("ready_for_validation")
    if ready is not None:
        return bool(ready)
    
    # Check status - done tasks are ready for QA
    status = task.get("status", "")
    return str(status).lower() in ("done", "validated")
