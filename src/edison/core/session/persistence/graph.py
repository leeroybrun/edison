"""Session activity logging and task linking helpers.

This module now uses task/QA files as the single source of truth.
Task and QA relationships are stored in the YAML frontmatter of task/QA files,
not in the session JSON.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from ...task import TaskManager, TaskRepository
from ...utils.time import utc_timestamp as io_utc_timestamp
from edison.core.utils.paths import PathResolver
from ..core.id import validate_session_id
from .repository import SessionRepository


def _load_or_create_session(session_id: str) -> Dict[str, Any]:
    """Load session or create minimal session dict if not found."""
    from edison.core.config.domains.workflow import WorkflowConfig
    sid = validate_session_id(session_id)
    repo = SessionRepository()
    sess = repo.get(sid)
    if sess:
        return sess.to_dict()
    # Return minimal session structure for creation
    # Use initial state from config
    initial_state = WorkflowConfig().get_initial_state("session")
    return {
        "id": sid,
        "state": initial_state,
        "meta": {},
    }


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    """Save session data."""
    from ..core.models import Session
    sid = validate_session_id(session_id)
    repo = SessionRepository()
    entity = Session.from_dict({**data, "id": sid})
    repo.save(entity)


def register_task(
    session_id: str,
    task_id: str,
    *,
    owner: str,
    status: str,
    qa_id: Optional[str] = None,
) -> None:
    """Register a task event in the session.

    The task file remains the single source of truth, but we keep a small
    `session.tasks` index for UX (fast session status rendering) and an
    activity log for auditability.
    """
    sid = validate_session_id(session_id)
    now = io_utc_timestamp()
    
    # Update session index + activity log (task file updated by workflow)
    sess = _load_or_create_session(sid)
    tasks = sess.setdefault("tasks", {})
    if isinstance(tasks, dict):
        entry = tasks.get(task_id) if isinstance(tasks.get(task_id), dict) else {}
        entry = dict(entry)
        entry.update({"status": status, "owner": owner})
        if qa_id:
            entry["qaId"] = qa_id
        tasks[task_id] = entry
    sess.setdefault("activityLog", []).append({
        "timestamp": now,
        "message": f"Task {task_id} registered with status {status}",
    })
    save_session(sid, sess)


def register_qa(
    session_id: str,
    task_id: str,
    qa_id: str,
    *,
    status: str,
    round_no: int = 1,
) -> None:
    """Register a QA registration event in session activity log.
    
    NOTE: This function no longer updates the QA file - QA files
    are updated directly by TaskQAWorkflow. This function only logs
    the activity in the session for audit purposes.
    
    The QA file is the single source of truth for QA metadata.
    """
    sid = validate_session_id(session_id)
    now = io_utc_timestamp()
    
    # Update session activity log only (QA file updated by workflow)
    sess = _load_or_create_session(sid)
    sess.setdefault("activityLog", []).append({
        "timestamp": now,
        "message": f"QA {qa_id} registered for task {task_id} with status {status}",
    })
    save_session(sid, sess)


def link_tasks(session_id: str, parent_id: str, child_id: str) -> None:
    """Link parent → child in task files.
    
    Updates both task files with the relationship.
    Session ID is validated but not used (kept for API compatibility).
    """
    validate_session_id(session_id)  # Validate but don't use
    task_repo = TaskRepository()
    
    parent = task_repo.get(parent_id)
    child = task_repo.get(child_id)
    
    if parent:
        if child_id not in parent.child_ids:
            parent.child_ids.append(child_id)
            task_repo.save(parent)
    
    if child:
        child.parent_id = parent_id
        task_repo.save(child)


def create_merge_task(session_id: str, branch_name: str, base_branch: str) -> str:
    """Create a task to merge the session worktree back to base branch."""
    task_id = f"merge-{session_id}"
    title = f"Merge session {session_id} ({branch_name}) into {base_branch}"
    desc = (
        f"Merge worktree branch `{branch_name}` into `{base_branch}`.\\n\\n"
        f"- **Session:** {session_id}\\n"
        f"- **Branch:** {branch_name}\\n"
        f"- **Base:** {base_branch}\\n"
    )
    
    # Create task file using TaskManager
    task_mgr = TaskManager()
    task_mgr.create_task(task_id, title, description=desc, session_id=session_id)
    
    return task_id
