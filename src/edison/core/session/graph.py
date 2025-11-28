"""Session task and QA graph management."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from ..task import TaskManager
from ..utils.time import utc_timestamp as io_utc_timestamp
from ..qa.evidence import EvidenceService
from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_management_paths
from .id import validate_session_id
from .repository import SessionRepository
from .models import TaskEntry, QAEntry, Session


def _load_or_create_session(session_id: str) -> Dict[str, Any]:
    """Load session or create minimal session dict if not found."""
    sid = validate_session_id(session_id)
    repo = SessionRepository()
    sess = repo.get(sid)
    if sess:
        return sess.to_dict()
    # Return minimal session structure for creation
    return {
        "id": sid,
        "state": "wip",
        "tasks": {},
        "qa": {},
        "meta": {},
    }


def save_session(session_id: str, data: Dict[str, Any]) -> None:
    """Save session data."""
    sid = validate_session_id(session_id)
    repo = SessionRepository()
    entity = Session.from_dict({**data, "id": sid})
    repo.save(entity)


def _upsert_task_entry(
    session: Dict[str, Any],
    task_id: str,
    *,
    owner: str,
    status: str,
    qa_id: Optional[str] = None,
) -> Dict[str, Any]:
    tasks = session.setdefault("tasks", {})
    if not isinstance(tasks, dict):
        tasks = {}
        session["tasks"] = tasks

    entry = tasks.get(task_id)
    now = io_utc_timestamp()

    if isinstance(entry, dict):
        entry.setdefault("recordId", task_id)
        entry.setdefault("owner", owner)
        entry["status"] = status
        if qa_id is not None:
            entry.setdefault("qaId", qa_id)
        entry.setdefault("childIds", entry.get("childIds") or [])
        entry.setdefault("parentId", entry.get("parentId"))
        entry.setdefault("automation", entry.get("automation") or {})
        entry.setdefault("notes", entry.get("notes") or [])
        entry.setdefault("claimedAt", entry.get("claimedAt") or now)
        entry["lastActive"] = now
    else:
        entry_obj = TaskEntry(
            record_id=task_id,
            status=status,
            owner=owner,
            qa_id=qa_id,
        )
        entry = entry_obj.to_dict()

    tasks[task_id] = entry
    return entry

def _upsert_qa_entry(
    session: Dict[str, Any],
    qa_id: str,
    task_id: str,
    *,
    status: str,
    round_no: int = 1,
) -> Dict[str, Any]:
    qa_map = session.setdefault("qa", {})
    if not isinstance(qa_map, dict):
        qa_map = {}
        session["qa"] = qa_map

    entry = qa_map.get(qa_id)
    if isinstance(entry, dict):
        entry.setdefault("recordId", qa_id)
        entry.setdefault("taskId", task_id)
        entry["status"] = status
        entry.setdefault("round", entry.get("round", round_no))
        entry.setdefault("evidence", entry.get("evidence") or [])
        entry.setdefault("validators", entry.get("validators") or [])
    else:
        entry_obj = QAEntry(
            record_id=qa_id,
            task_id=task_id,
            status=status,
            round=round_no,
        )
        entry = entry_obj.to_dict()

    qa_map[qa_id] = entry
    return entry

def register_task(
    session_id: str,
    task_id: str,
    *,
    owner: str,
    status: str,
    qa_id: Optional[str] = None,
) -> None:
    """Register or update a task entry in the session graph."""
    sess = _load_or_create_session(session_id)
    _upsert_task_entry(sess, task_id, owner=owner, status=status, qa_id=qa_id)
    save_session(session_id, sess)

def register_qa(
    session_id: str,
    task_id: str,
    qa_id: str,
    *,
    status: str,
    round_no: int = 1,
) -> None:
    """Register or update a QA entry in the session graph."""
    sess = _load_or_create_session(session_id)
    entry = _upsert_qa_entry(sess, qa_id, task_id, status=status, round_no=round_no)
    # Ensure task entry points at this QA id (preserve existing task status)
    tasks = sess.get("tasks", {})
    existing_task = tasks.get(task_id, {})
    task_status = existing_task.get("status", "unknown") if isinstance(existing_task, dict) else "unknown"
    _upsert_task_entry(sess, task_id, owner=sess.get("meta", {}).get("owner", "_unassigned_"), status=task_status, qa_id=entry["recordId"])
    save_session(session_id, sess)

def update_record_status(
    session_id: str,
    record_id: str,
    record_type: str,
    status: str,
) -> None:
    """Update status for a task or QA entry in the session graph."""
    sess = _load_or_create_session(session_id)
    kind = "task" if record_type == "task" else "qa"
    if kind == "task":
        tasks = sess.get("tasks", {})
        if isinstance(tasks, dict) and record_id in tasks:
            tasks[record_id]["status"] = status
            tasks[record_id]["lastActive"] = io_utc_timestamp()
    else:
        qa_map = sess.get("qa", {})
        if isinstance(qa_map, dict) and record_id in qa_map:
            qa_map[record_id]["status"] = status
    save_session(session_id, sess)

def link_tasks(session_id: str, parent_id: str, child_id: str) -> None:
    """Link parent → child in the session task graph."""
    sess = _load_or_create_session(session_id)
    tasks = sess.setdefault("tasks", {})
    if not isinstance(tasks, dict):
        tasks = {}
        session["tasks"] = tasks

    parent = tasks.get(parent_id) or TaskEntry(
        record_id=parent_id,
        status="unknown",
        owner=sess.get("meta", {}).get("owner", "_unassigned_"),
    ).to_dict()
    child = tasks.get(child_id) or TaskEntry(
        record_id=child_id,
        status="unknown",
        owner=sess.get("meta", {}).get("owner", "_unassigned_"),
    ).to_dict()

    # Update linkage
    parent_children = set(parent.get("childIds") or [])
    parent_children.add(child_id)
    parent["childIds"] = sorted(parent_children)
    child["parentId"] = parent_id

    tasks[parent_id] = parent
    tasks[child_id] = child
    save_session(session_id, sess)

def gather_cluster(session: Dict[str, Any], root_task: str) -> List[Dict[str, Any]]:
    """Gather a connected cluster of tasks rooted at ``root_task``."""
    tasks = session.get("tasks", {})
    if not isinstance(tasks, dict):
        return []

    cluster: List[Dict[str, Any]] = []
    queue: List[str] = [root_task]
    seen: set[str] = set()

    while queue:
        tid = queue.pop(0)
        if tid in seen:
            continue
        seen.add(tid)
        entry = tasks.get(tid)
        if not isinstance(entry, dict):
            continue
        children = [str(c) for c in entry.get("childIds", []) if isinstance(c, str)]
        queue.extend([c for c in children if c not in seen])
        cluster.append(
            {
                "taskId": tid,
                "taskStatus": str(entry.get("status") or "unknown"),
                "children": children,
                "qaId": str(entry.get("qaId") or f"{tid}-qa"),
            }
        )
    return cluster

def build_validation_bundle(session_id: str, root_task: str) -> Dict[str, Any]:
    """Build a validation bundle manifest for a task hierarchy."""
    sid = validate_session_id(session_id)
    sess = _load_or_create_session(sid)
    cluster = gather_cluster(sess, root_task)

    tasks_payload: List[Dict[str, Any]] = []

    for item in cluster:
        task_id = item["taskId"]
        qa_id = item["qaId"]
        children = item["children"]
        task_status = item["taskStatus"]

        # Resolve task/QA paths (prefer session scope, fall back to global)
        t_path: Optional[Path]
        qa_path: Optional[Path]

        # Use TaskRepository to find task path
        try:
            from ..task import TaskRepository
            task_repo = TaskRepository()
            t_path = task_repo._find_entity_path(task_id)
        except Exception:
            t_path = None

        # Use QARepository to find QA path
        try:
            from ..qa.repository import QARepository
            qa_repo = QARepository()
            qa_path = qa_repo._find_entity_path(task_id)
        except Exception:
            qa_path = None

        qa_status = qa_path.parent.name if qa_path is not None else "missing"

        # Evidence directory (base dir for round-* dirs); tolerate missing evidence
        try:
            svc = EvidenceService(task_id)
            evidence_dir = str(svc.get_evidence_root())
        except Exception:
            # Fallback to conventional location
            root = PathResolver.resolve_project_root()
            mgmt_paths = get_management_paths(root)
            evidence_dir = str(mgmt_paths.get_qa_root() / "validation-evidence" / task_id)

        tasks_payload.append(
            {
                "taskId": task_id,
                "taskStatus": task_status,
                "taskPath": str(t_path) if t_path is not None else "",
                "qaId": qa_id,
                "qaStatus": qa_status,
                "qaPath": str(qa_path) if qa_path is not None else "",
                "children": children,
                "evidenceDir": evidence_dir,
            }
        )

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
    task_mgr.create_task(task_id, title, desc)

    # Register in session graph
    register_task(session_id, task_id, owner="_unassigned_", status="todo")
    
    return task_id
