"""Delegation helpers used by Edison tests.

This module provides a small surface for routing and delegating tasks to
agents in a test-friendly manner (no external calls). The refactor adds
helpers, docstrings, reduced complexity, and clearer errors.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from edison.core.utils.time import utc_timestamp
from ..config import ConfigManager
from .. import task as _task


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
    for key in ('ZEN_MCP_CLINK', 'EDISON_DELEGATION_CLINK', 'EDISON_CLINK_TARGET'):
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


# === Group 4 (Task & Delegation) additions ===

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
    if parent_task_id:
        child_id = _task.next_child_id(parent_task_id)
    else:
        # Fallback ID generation
        import uuid
        child_id = f"delegated-{uuid.uuid4().hex[:8]}"

    _task.create_task_record(child_id, description)

    updates = {
        'agent': agent,
        'status': 'pending',
        'delegated_at': utc_timestamp(),
    }
    if parent_task_id:
        updates['parent_task_id'] = parent_task_id
    if session_id:
        updates['session_id'] = session_id

    _task.update_task_record(
        child_id,
        updates,
        operation='delegate',
    )

    # Update parent task's child_tasks list
    if parent_task_id:
        parent = _task.load_task_record(parent_task_id)
        child_tasks = parent.get('child_tasks', [])
        if child_id not in child_tasks:
            child_tasks.append(child_id)
        _task.update_task_record(
            parent_task_id,
            {'child_tasks': child_tasks},
            operation='add-child',
        )

    return child_id

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
    counts = {'success': 0, 'failure': 0, 'pending': 0}
    in_progress = 0
    for cid in child_ids:
        try:
            rec = _task.load_task_record(cid)
            cls = _classify_status(rec.get('status'))
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
    parent = _task.load_task_record(parent_task_id)
    child_ids: List[str] = parent.get('child_tasks', []) or []
    summary = _compute_child_status_summary(child_ids)

    # Persist summary on parent for visibility
    _task.update_task_record(
        parent_task_id,
        {
            'child_status_summary': {
                'total': summary['total'],
                'completed': summary['counts']['success'],
                'failed': summary['counts']['failure'],
                'pending': summary['counts']['pending'],
                'in_progress': summary['in_progress'],
            },
            **({'status': summary['status']} if summary['status'] in ('completed', 'failure', 'partial_failure') else {}),
        },
        operation='aggregate-children',
    )

    return {k: summary[k] for k in ('total', 'counts', 'status')}


__all__ = ['get_role_mapping', 'map_role', 'route_task', 'delegate_task', 'aggregate_child_results']
