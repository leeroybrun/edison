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


def has_blockers(ctx: Mapping[str, Any]) -> bool:
    """Shared "has blockers" guard across domains.

    This guard is intentionally shared (used by multiple state machines) and
    inspects whichever entity is present in context.

    Supported context shapes:
    - Task transitions: ctx["task"] mapping with "blocked" or "blockers"
    - Session transitions: ctx["session"] mapping with "blocked"/"blockers" or
      an explicit "blocker_reason"/"reason" injected by CLI/workflows
    - Generic: ctx["blocked"]/ctx["blockers"]/ctx["blocker_reason"]
    """
    task = ctx.get("task")
    if isinstance(task, Mapping):
        return bool(
            task.get("blocked")
            or task.get("blockers")
            or task.get("blocker_reason")
            or task.get("reason")
        )

    session = ctx.get("session")
    if isinstance(session, Mapping):
        return bool(
            session.get("blocked")
            or session.get("blockers")
            or session.get("blocker_reason")
            or session.get("reason")
        )

    return bool(ctx.get("blocked") or ctx.get("blockers") or ctx.get("blocker_reason") or ctx.get("reason"))


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
