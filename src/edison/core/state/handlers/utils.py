"""Shared utilities for state machine handlers.

This module provides common utilities used by guards, conditions, and actions.
"""
from __future__ import annotations

from typing import Any, Mapping


def get_task_id_from_context(ctx: Mapping[str, Any]) -> str | None:
    """Extract task_id from context in various forms.
    
    Searches for task_id in the following order:
    1. Direct task_id key
    2. From QA dict (task_id or taskId)
    3. From task dict (id)
    4. From entity_id if entity_type is qa
    
    Args:
        ctx: Context mapping containing task information
        
    Returns:
        Task ID string or None if not found
    """
    # Direct task_id
    if ctx.get("task_id"):
        return str(ctx["task_id"])

    # From QA dict
    qa = ctx.get("qa")
    if isinstance(qa, Mapping):
        tid = qa.get("task_id") or qa.get("taskId")
        if tid:
            return str(tid)

    # From task dict
    task = ctx.get("task")
    if isinstance(task, Mapping):
        tid = task.get("id")
        if tid:
            return str(tid)

    # From entity_id if entity_type is qa
    if ctx.get("entity_type") == "qa" and ctx.get("entity_id"):
        return str(ctx["entity_id"])

    return None


__all__ = ["get_task_id_from_context"]






