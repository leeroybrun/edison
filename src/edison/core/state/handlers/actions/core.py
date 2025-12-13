"""Core action functions for state machine transitions.

Actions are side-effect functions executed during state transitions.
They modify context, persist state, or trigger external systems.
"""
from __future__ import annotations

from typing import Any, MutableMapping


def record_completion_time(ctx: MutableMapping[str, Any]) -> None:
    """Record completion timestamp in context.
    
    Sets the completion timestamp for the entity being transitioned.
    
    Args:
        ctx: Mutable context dict
    """
    from edison.core.utils.time import utc_timestamp
    
    ctx.setdefault("_timestamps", {})["completed"] = utc_timestamp()
    
    # Also record in entity-specific locations if present
    if "task" in ctx and isinstance(ctx["task"], MutableMapping):
        ctx["task"].setdefault("meta", {})["completedAt"] = utc_timestamp()
    if "session" in ctx and isinstance(ctx["session"], MutableMapping):
        ctx["session"].setdefault("meta", {})["completedAt"] = utc_timestamp()


def record_blocker_reason(ctx: MutableMapping[str, Any]) -> None:
    """Record blocker reason in context.
    
    Captures the reason for blocking from session or task context.
    
    Args:
        ctx: Mutable context dict
    """
    from edison.core.utils.time import utc_timestamp
    
    reason = None
    
    # Try to get reason from session
    session = ctx.get("session", {})
    if isinstance(session, MutableMapping):
        reason = session.get("reason") or session.get("blocker_reason")
    
    # Fall back to task
    if not reason:
        task = ctx.get("task", {})
        if isinstance(task, MutableMapping):
            reason = task.get("reason") or task.get("blocker_reason")
    
    # Record in context
    ctx.setdefault("_actions", []).append(f"record_blocker_reason:{reason or ''}")
    ctx.setdefault("_blockers", {})["reason"] = reason
    ctx.setdefault("_blockers", {})["recorded_at"] = utc_timestamp()


def record_closed(ctx: MutableMapping[str, Any]) -> None:
    """Record session closed timestamp.
    
    Args:
        ctx: Mutable context dict
    """
    from edison.core.utils.time import utc_timestamp
    
    ctx.setdefault("_timestamps", {})["closed"] = utc_timestamp()
    
    if "session" in ctx and isinstance(ctx["session"], MutableMapping):
        ctx["session"].setdefault("meta", {})["closedAt"] = utc_timestamp()


def log_transition(ctx: MutableMapping[str, Any]) -> None:
    """Log the state transition for debugging.
    
    Args:
        ctx: Mutable context dict containing transition info
    """
    import logging
    logger = logging.getLogger("edison.state.actions")
    
    entity_type = ctx.get("entity_type", "unknown")
    entity_id = ctx.get("entity_id", "unknown")
    from_state = ctx.get("from_state", "?")
    to_state = ctx.get("to_state", "?")
    
    logger.info(
        "State transition: %s/%s %s -> %s",
        entity_type, entity_id, from_state, to_state
    )


