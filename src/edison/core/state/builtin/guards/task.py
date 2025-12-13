"""Task-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""
from __future__ import annotations

from typing import Any, Mapping


def can_start_task(ctx: Mapping[str, Any]) -> bool:
    """Task can start only if claimed by current session.
    
    FAIL-CLOSED: Returns False if any required data is missing.
    
    Prerequisites:
    - Task must exist in context
    - Session must exist in context
    - Task must be claimed by the session (matching session_id)
    
    Args:
        ctx: Context with 'task' and 'session' dicts
        
    Returns:
        True if task is claimed by current session
    """
    task = ctx.get("task")
    session = ctx.get("session")
    
    if not isinstance(task, Mapping) or not isinstance(session, Mapping):
        return False  # FAIL-CLOSED: missing context
    
    task_session = task.get("session_id") or task.get("sessionId")
    session_id = session.get("id")
    
    if not task_session or not session_id:
        return False  # FAIL-CLOSED: missing IDs
    
    return str(task_session) == str(session_id)


def can_finish_task(ctx: Mapping[str, Any]) -> bool:
    """Task can finish only if implementation report exists.
    
    FAIL-CLOSED: Returns False if evidence is missing.
    
    Prerequisites:
    - Task ID must be in context (via 'task.id' or 'entity_id')
    - Implementation report JSON must exist in evidence directory
    
    Args:
        ctx: Context with task ID (via 'task' dict or 'entity_id') and optionally 'project_root'
        
    Returns:
        True if implementation report exists for latest round
    """
    # Try to get task_id from various context patterns
    task_id = None
    
    # Pattern 1: task dict with id
    task = ctx.get("task")
    if isinstance(task, Mapping):
        task_id = task.get("id")
    
    # Pattern 2: entity_id (from transition_entity)
    if not task_id:
        task_id = ctx.get("entity_id")
    
    if not task_id:
        return False  # FAIL-CLOSED: no task ID found
    
    # Get project_root from context if available (for isolated test environments)
    project_root = ctx.get("project_root")
    
    # Check implementation report exists
    try:
        from edison.core.qa.evidence import EvidenceService
        ev_svc = EvidenceService(str(task_id), project_root=project_root)
        latest = ev_svc.get_current_round()
        if latest is not None:
            report = ev_svc.read_implementation_report(latest)
            return bool(report)
    except Exception:
        pass
    
    return False  # FAIL-CLOSED: no evidence found


def has_implementation_report(ctx: Mapping[str, Any]) -> bool:
    """Check if implementation report exists for the task.
    
    Alias for can_finish_task with clearer semantic meaning.
    
    Args:
        ctx: Context with 'task' dict containing 'id'
        
    Returns:
        True if implementation report exists
    """
    return can_finish_task(ctx)


def has_blockers(ctx: Mapping[str, Any]) -> bool:
    """Check if task has blockers preventing progress.
    
    FAIL-CLOSED: Returns False if no blockers can be determined.
    
    Args:
        ctx: Context with 'task' dict
        
    Returns:
        True if task has blockers
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED: can't determine blockers
    
    return bool(task.get("blocked") or task.get("blockers"))


def requires_rollback_reason(ctx: Mapping[str, Any]) -> bool:
    """Check if task has rollback reason for done->wip transition.
    
    FAIL-CLOSED: Returns False if rollback reason is missing.
    
    Args:
        ctx: Context with 'task' dict
        
    Returns:
        True if rollback reason is present
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED
    
    reason = (
        task.get("rollbackReason")
        or task.get("rollback_reason")
        or ""
    )
    return bool(str(reason).strip())
