"""Session task and QA graph management.

This module now uses task/QA files as the single source of truth.
Task and QA relationships are stored in the YAML frontmatter of task/QA files,
not in the session JSON. Use TaskIndex to query task/QA data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from ...task import TaskManager, TaskRepository, TaskIndex
from ...qa.workflow.repository import QARepository
from ...utils.time import utc_timestamp as io_utc_timestamp
from ...qa.evidence import EvidenceService
from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_management_paths
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
    """Register a task registration event in session activity log.
    
    NOTE: This function no longer updates the task file - task files
    are updated directly by TaskQAWorkflow. This function only logs
    the activity in the session for audit purposes.
    
    The task file is the single source of truth for task metadata.
    """
    sid = validate_session_id(session_id)
    now = io_utc_timestamp()
    
    # Update session activity log only (task file updated by workflow)
    sess = _load_or_create_session(sid)
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


def gather_cluster(session_id: str, root_task: str) -> List[Dict[str, Any]]:
    """Gather a connected cluster of tasks rooted at ``root_task``.
    
    Uses TaskIndex to traverse the task graph from files.
    """
    index = TaskIndex()
    graph = index.get_task_graph(session_id=session_id)
    
    cluster: List[Dict[str, Any]] = []
    queue: List[str] = [root_task]
    seen: set[str] = set()
    
    while queue:
        tid = queue.pop(0)
        if tid in seen:
            continue
        seen.add(tid)
        
        task_summary = graph.tasks.get(tid)
        if not task_summary:
            continue
        
        children = task_summary.child_ids
        queue.extend([c for c in children if c not in seen])
        
        # Derive QA ID from task ID
        qa_id = f"{tid}-qa"
        
        cluster.append({
            "taskId": tid,
            "taskStatus": task_summary.state,
            "children": children,
            "qaId": qa_id,
        })
    
    return cluster


def build_validation_bundle(session_id: str, root_task: str) -> Dict[str, Any]:
    """Build a validation bundle manifest for a task hierarchy.
    
    Uses TaskIndex and TaskRepository to gather data from files.
    """
    sid = validate_session_id(session_id)
    cluster = gather_cluster(sid, root_task)
    
    task_repo = TaskRepository()
    qa_repo = QARepository()
    
    tasks_payload: List[Dict[str, Any]] = []
    
    for item in cluster:
        task_id = item["taskId"]
        qa_id = item["qaId"]
        children = item["children"]
        task_status = item["taskStatus"]
        
        # Resolve task/QA paths
        t_path: Optional[Path] = None
        qa_path: Optional[Path] = None
        
        try:
            t_path = task_repo._find_entity_path(task_id)
        except Exception:
            pass
        
        try:
            qa_path = qa_repo._find_entity_path(qa_id)
        except Exception:
            pass
        
        qa_status = qa_path.parent.name if qa_path is not None else "missing"
        
        # Evidence directory
        try:
            svc = EvidenceService(task_id)
            evidence_dir = str(svc.get_evidence_root())
        except Exception:
            from edison.core.qa._utils import get_evidence_base_path
            root = PathResolver.resolve_project_root()
            evidence_dir = str(get_evidence_base_path(root) / task_id)
        
        tasks_payload.append({
            "taskId": task_id,
            "taskStatus": task_status,
            "taskPath": str(t_path) if t_path is not None else "",
            "qaId": qa_id,
            "qaStatus": qa_status,
            "qaPath": str(qa_path) if qa_path is not None else "",
            "children": children,
            "evidenceDir": evidence_dir,
        })
    
    return {
        "sessionId": sid,
        "rootTask": root_task,
        "tasks": tasks_payload,
    }


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
