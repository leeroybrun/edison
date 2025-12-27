"""Test helper functions for delegation operations.

This module provides test-friendly delegation helpers that wrap the canonical
task and config modules with simplified APIs for test scenarios.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, List

from edison.core.config import ConfigManager
from edison.core.utils.time import utc_timestamp
from edison.core.task import TaskRepository, Task


__all__ = ['get_role_mapping', 'map_role', 'route_task', 'delegate_task', 'aggregate_child_results']


def get_role_mapping(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Return role mapping from configuration.

    Args:
        cfg: Optional pre-loaded config dict; loaded from ConfigManager if None.

    Returns:
        Dict[str, str]: Mapping from generic role → concrete target role.
    """
    cfg = cfg or ConfigManager().load_config()
    return ((cfg.get('delegation') or {}).get('roleMapping') or {})


def map_role(generic_role: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    """Map a generic role to a concrete target using config mapping.

    Falls back to the provided role if no mapping exists.
    """
    mapping = get_role_mapping(cfg)
    return mapping.get(generic_role, generic_role)


def _clink_target() -> Optional[str]:
    # Allow multiple env names; first non-empty wins.
    for key in ('PAL_MCP_CLINK', 'EDISON_DELEGATION_CLINK', 'EDISON_CLINK_TARGET'):
        val = os.environ.get(key)
        if val:
            return val
    return None


def route_task(generic_role: str, continuation_id: Optional[str] = None,
               clink: Optional[str] = None,
               cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Produce a routing envelope for a task (no side effects).

    Args:
        generic_role: Logical role name (e.g., "writer", "tester").
        continuation_id: Optional correlation id for multi-step flows.
        clink: Optional explicit clink target (env fallback is used otherwise).
        cfg: Optional config override for mapping.

    Returns:
        Dict[str, Any]: Envelope with routing details.
    """
    target_role = map_role(generic_role, cfg)
    envelope = {
        'generic_role': generic_role,
        'target_role': target_role,
        'continuation_id': continuation_id,
        'clink': clink or _clink_target(),
    }
    return envelope


def delegate_task(
    description: str,
    agent: str,
    parent_task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """Create a child task record, assign an agent, and return its id.

    No external agent call is made; this records intent for orchestration.

    Args:
        description: Description for the delegated work item.
        agent: Logical/CLI agent name.
        parent_task_id: Optional parent task linkage.
        session_id: Optional session linkage.

    Returns:
        str: The child task identifier.
    """
    repo = TaskRepository()

    # Create child task
    task = Task.create(
        task_id=f"task-delegated-{utc_timestamp().replace(':', '-').replace('.', '-')}",
        title=description,
        description=description,
        session_id=session_id,
        state="pending",
    )

    if parent_task_id:
        task.parent_id = parent_task_id
        # Update parent's children list
        parent = repo.get(parent_task_id)
        if parent and task.id not in parent.children:
            parent.children.append(task.id)
            repo.save(parent)

    repo.create(task)

    # Store agent metadata (note: Task model doesn't have agent field,
    # but this is for delegation tracking in tests)
    # We'll use tags for this purpose
    task.tags = [f"agent:{agent}", f"delegated_at:{utc_timestamp()}"]
    repo.save(task)

    return task.id

def _classify_status(status: str) -> str:
    """Normalize a raw task status to one of: success|failure|pending|in_progress."""
    s = str(status or 'pending').lower()
    if s in ('success', 'completed', 'ok', 'done'):
        return 'success'
    if s in ('failure', 'failed', 'error'):
        return 'failure'
    if s in ('in_progress', 'wip', 'running'):
        return 'in_progress'
    return 'pending'


def _compute_child_status_summary(child_ids: List[str]) -> Dict[str, Any]:
    """Compute counts and overall status from a list of child task ids."""
    repo = TaskRepository()
    counts = {'success': 0, 'failure': 0, 'pending': 0}
    in_progress = 0
    for cid in child_ids:
        try:
            task = repo.get(cid)
            cls = _classify_status(task.state if task else 'pending')
        except Exception:
            cls = 'pending'
        if cls == 'in_progress':
            in_progress += 1
        elif cls in counts:
            counts[cls] += 1
        else:
            counts['pending'] += 1

    total = len(child_ids)
    if total == 0:
        overall = 'pending'
    elif counts['success'] == total:
        overall = 'completed'
    elif counts['failure'] > 0 and counts['success'] > 0:
        overall = 'partial_failure'
    elif counts['failure'] > 0 and counts['success'] == 0 and counts['pending'] == 0 and in_progress == 0:
        overall = 'failure'
    elif counts['pending'] == total:
        overall = 'pending'
    else:
        overall = 'in_progress'

    return {
        'total': total,
        'counts': counts,
        'in_progress': in_progress,
        'status': overall,
    }


def aggregate_child_results(parent_task_id: str) -> Dict[str, Any]:
    """Aggregate child task statuses for a parent task.

    Returns
    -------
    Dict[str, Any]
        A summary with counts and an overall status:
        { 'total': N,
          'counts': {'success': x, 'failure': y, 'pending': z},
          'status': 'completed' | 'partial_failure' | 'in_progress' | 'pending' }
    """
    repo = TaskRepository()
    parent = repo.get(parent_task_id)
    if not parent:
        raise ValueError(f"Parent task not found: {parent_task_id}")

    child_ids: List[str] = parent.children or []
    summary = _compute_child_status_summary(child_ids)

    # Update parent state based on aggregation
    if summary['status'] in ('completed', 'failure', 'partial_failure'):
        parent.state = summary['status']
        repo.save(parent)

    return {k: summary[k] for k in ('total', 'counts', 'status')}
