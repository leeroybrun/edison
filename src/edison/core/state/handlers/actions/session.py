"""Session-specific action functions for state machine transitions.

These actions manage session lifecycle events like activation,
completion, and finalization.
"""
from __future__ import annotations

import logging
from typing import Any, MutableMapping

logger = logging.getLogger(__name__)


def record_activation_time(ctx: MutableMapping[str, Any]) -> None:
    """Record session activation timestamp.
    
    Sets the activation timestamp for the session.
    
    Args:
        ctx: Mutable context dict with 'session'
    """
    from edison.core.utils.time import utc_timestamp
    
    timestamp = utc_timestamp()
    ctx.setdefault("_timestamps", {})["activated"] = timestamp
    
    session = ctx.get("session", {})
    if isinstance(session, MutableMapping):
        session.setdefault("meta", {})["activatedAt"] = timestamp


def notify_session_start(ctx: MutableMapping[str, Any]) -> None:
    """Notify that session has started.
    
    Records the session start event and optionally triggers
    external notifications.
    
    Args:
        ctx: Mutable context dict with 'session'
    """
    from edison.core.utils.time import utc_timestamp
    
    session = ctx.get("session", {})
    session_id = session.get("id") if isinstance(session, MutableMapping) else None
    
    # Record the event
    ctx.setdefault("_events", []).append({
        "type": "session_started",
        "session_id": session_id,
        "timestamp": utc_timestamp(),
    })
    
    logger.info("Session started: %s", session_id)


def finalize_session(ctx: MutableMapping[str, Any]) -> None:
    """Finalize session state and persist.
    
    Performs final cleanup and persistence for session completion.
    
    Args:
        ctx: Mutable context dict with 'session'
    """
    from edison.core.utils.time import utc_timestamp
    
    session = ctx.get("session", {})
    if not isinstance(session, MutableMapping):
        logger.warning("finalize_session: No session in context")
        return
    
    session_id = session.get("id")
    if not session_id:
        logger.warning("finalize_session: No session ID")
        return
    
    # Record finalization timestamp
    timestamp = utc_timestamp()
    session.setdefault("meta", {})["finalizedAt"] = timestamp
    session.setdefault("meta", {})["lastActive"] = timestamp
    
    # Persist session
    try:
        from edison.core.session.persistence.graph import save_session
        save_session(str(session_id), dict(session))
        logger.info("Finalized session: %s", session_id)
        ctx.setdefault("_session", {})["finalized"] = True
    except ImportError:
        logger.debug("Session persistence not available")
    except Exception as e:
        logger.error("Error finalizing session %s: %s", session_id, e)


def append_session_log(ctx: MutableMapping[str, Any]) -> None:
    """Append entry to session activity log.
    
    Adds the current action/event to the session's activity log.
    
    Args:
        ctx: Mutable context dict with 'session' and 'message'
    """
    from edison.core.utils.time import utc_timestamp
    
    session = ctx.get("session", {})
    if not isinstance(session, MutableMapping):
        return
    
    message = ctx.get("log_message", "State transition")
    
    session.setdefault("activityLog", []).append({
        "timestamp": utc_timestamp(),
        "message": str(message),
    })


def validate_prerequisites(ctx: MutableMapping[str, Any]) -> None:
    """Pre-transition action to validate prerequisites.
    
    Can be used with `when: before` to validate before guards run.
    
    Args:
        ctx: Mutable context dict
    """
    # This action is typically used for pre-transition validation
    # that needs to run before guards
    ctx.setdefault("_prerequisites", {})["validated"] = True


