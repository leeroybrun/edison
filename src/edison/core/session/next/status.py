"""Status inference functions for session next computation.

Functions for inferring task and QA status from filesystem state.
"""
from __future__ import annotations

from edison.core import task


def infer_task_status(task_id: str) -> str:
    """Infer task status from filesystem location."""
    try:
        p = task.find_record(task_id, "task")
        return task.infer_status_from_path(p, "task") or "unknown"
    except FileNotFoundError:
        return "missing"


def infer_qa_status(task_id: str) -> str:
    """Infer QA status from filesystem location."""
    try:
        p = task.find_record(task_id, "qa")
        return task.infer_status_from_path(p, "qa") or "missing"
    except FileNotFoundError:
        return "missing"
