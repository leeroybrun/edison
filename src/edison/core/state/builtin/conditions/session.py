"""Session-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from typing import Any, Mapping


def has_blocker_reason(ctx: Mapping[str, Any]) -> bool:
    """Check if blocker reason is present.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if blocker reason exists
    """
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        reason = session.get("blocker_reason") or session.get("reason")
        if reason:
            return bool(str(reason).strip())
        meta = session.get("meta", {})
        if isinstance(meta, Mapping):
            meta_reason = meta.get("blockerReason") or meta.get("blocker_reason")
            return bool(str(meta_reason).strip()) if meta_reason else False
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

    session_id = session.get("id") or ctx.get("session_id")
    if not session_id:
        return False

    try:
        from edison.core.task import TaskIndex
        from edison.core.utils.paths import PathResolver

        project_root = ctx.get("project_root")
        index = TaskIndex(project_root=project_root or PathResolver.resolve_project_root())
        tasks = index.list_tasks_in_session(str(session_id))
    except Exception:
        return False

    # Fail-closed: if tasks exist and any isn't validated, block.
    for t in tasks:
        if str(t.state).lower() != "validated":
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

    if has_blocker_reason(ctx):
        return False
    
    # Check for active blockers list
    blockers = session.get("blockers", [])
    if isinstance(blockers, list) and len(blockers) > 0:
        return False
    
    return True
