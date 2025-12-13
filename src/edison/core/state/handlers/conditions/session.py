"""Session-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from typing import Any, Mapping


def validation_failed(ctx: Mapping[str, Any]) -> bool:
    """Check if validation has failed.
    
    Args:
        ctx: Context with 'session' or 'validation_results' dict
        
    Returns:
        True if validation failed
    """
    # Check explicit flag
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        if session.get("validation_failed") is not None:
            return bool(session.get("validation_failed"))
    
    # Check validation results
    validation = ctx.get("validation_results", {})
    if isinstance(validation, Mapping):
        failed = validation.get("failed_validators", [])
        if failed:
            return True
        blocking = validation.get("blocking_validators", [])
        if isinstance(blocking, list):
            return any(not v.get("passed") for v in blocking if isinstance(v, Mapping))
    
    return False


def dependencies_missing(ctx: Mapping[str, Any]) -> bool:
    """Check if dependencies are missing.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if dependencies are missing
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        return bool(session.get("deps_missing", False))
    
    return False


def has_blocker_reason(ctx: Mapping[str, Any]) -> bool:
    """Check if blocker reason is present.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if blocker reason exists
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        reason = session.get("reason") or session.get("blocker_reason")
        return bool(str(reason).strip()) if reason else False
    
    return False


def session_has_owner(ctx: Mapping[str, Any]) -> bool:
    """Check if session has an owner assigned.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if owner is assigned
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        meta = session.get("meta", {})
        if isinstance(meta, Mapping):
            owner = meta.get("owner")
            return bool(owner)
        return bool(session.get("owner"))
    
    return False


def all_tasks_validated(ctx: Mapping[str, Any]) -> bool:
    """Check if all tasks in session are validated.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if all tasks are validated
    """
    session = ctx.get("session", {})
    if not isinstance(session, Mapping):
        return False
    
    tasks = session.get("tasks", {})
    if not tasks:
        return True  # No tasks = nothing to validate
    
    if isinstance(tasks, Mapping):
        for task in tasks.values():
            if isinstance(task, Mapping):
                status = task.get("status", "")
                if str(status).lower() != "validated":
                    return False
    
    return True


def blockers_resolved(ctx: Mapping[str, Any]) -> bool:
    """Check if blockers have been resolved.
    
    Opposite of has_blocker_reason - returns True when no blockers remain.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if blockers are resolved (no active blockers)
    """
    session = ctx.get("session", {})
    if not isinstance(session, Mapping):
        return True  # No session = no blockers
    
    # Check if explicitly marked as blocked
    if session.get("blocked"):
        return False
    
    # Check for active blockers list
    blockers = session.get("blockers", [])
    if isinstance(blockers, list) and len(blockers) > 0:
        return False
    
    return True


