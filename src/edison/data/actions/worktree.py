"""Worktree-related action functions for state machine transitions.

These actions manage git worktrees for session isolation.
"""
from __future__ import annotations

import logging
from typing import Any, MutableMapping

logger = logging.getLogger(__name__)


def create_worktree(ctx: MutableMapping[str, Any]) -> None:
    """Create git worktree for the session.
    
    Creates an isolated git worktree directory for the session,
    allowing parallel development without branch conflicts.
    
    Prerequisites:
    - Session must exist in context with valid ID
    - Worktrees must be enabled in config
    
    Args:
        ctx: Mutable context dict with 'session' and optional 'config'
    """
    session = ctx.get("session", {})
    if not isinstance(session, MutableMapping):
        logger.warning("create_worktree: No session in context")
        return
    
    session_id = session.get("id")
    if not session_id:
        logger.warning("create_worktree: No session ID")
        return
    
    # Check if worktrees are enabled
    config = ctx.get("config", {})
    if isinstance(config, MutableMapping):
        worktrees_enabled = config.get("worktrees_enabled", False)
        if not worktrees_enabled:
            logger.debug("create_worktree: Worktrees not enabled in config")
            return
    
    # Try to create worktree
    try:
        from edison.core.session.worktree.manager import WorktreeManager
        manager = WorktreeManager()
        result = manager.create_for_session(str(session_id))
        
        if result:
            logger.info("Created worktree for session %s", session_id)
            ctx.setdefault("_worktree", {})["created"] = True
            ctx.setdefault("_worktree", {})["path"] = str(result.get("path", ""))
        else:
            logger.warning("Failed to create worktree for session %s", session_id)
            
    except ImportError:
        logger.debug("WorktreeManager not available")
    except Exception as e:
        logger.error("Error creating worktree for session %s: %s", session_id, e)


def cleanup_worktree(ctx: MutableMapping[str, Any]) -> None:
    """Cleanup worktree for completed session.
    
    Removes the git worktree directory for a session that has completed
    or is being archived.
    
    Args:
        ctx: Mutable context dict with 'session'
    """
    session = ctx.get("session", {})
    if not isinstance(session, MutableMapping):
        return
    
    session_id = session.get("id")
    if not session_id:
        return
    
    try:
        from edison.core.session.worktree.manager import WorktreeManager
        manager = WorktreeManager()
        manager.remove_for_session(str(session_id))
        
        logger.info("Cleaned up worktree for session %s", session_id)
        ctx.setdefault("_worktree", {})["removed"] = True
        
    except ImportError:
        logger.debug("WorktreeManager not available")
    except Exception as e:
        logger.error("Error cleaning up worktree for session %s: %s", session_id, e)
