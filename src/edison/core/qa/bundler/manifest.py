"""Validation bundle manifest builder.

This module builds a cluster manifest for validation, rooted at a parent task.
It is intentionally independent of session persistence (session JSON is not a
source of truth for task/QA relationships).

Sources of truth:
- Task/QA files (TaskRepository / QARepository)
- Parent/child relationships from task frontmatter (TaskIndex)
- Evidence directories (EvidenceService)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.time import utc_timestamp

from edison.core.task import TaskIndex, TaskRepository
from edison.core.qa.workflow.repository import QARepository
from edison.core.qa.evidence import EvidenceService
from edison.core.utils.paths import PathResolver


def _cluster_task_ids(root_task: str, *, graph) -> List[str]:

    queue: List[str] = [str(root_task)]
    seen: set[str] = set()
    ordered: List[str] = []

    while queue:
        tid = str(queue.pop(0))
        if tid in seen:
            continue
        seen.add(tid)
        ordered.append(tid)

        summary = graph.tasks.get(tid)
        children: set[str] = set(graph.get_children(tid))
        if summary:
            children.update([str(c) for c in (summary.child_ids or []) if c])

        for child_id in sorted(children):
            if child_id not in seen:
                queue.append(child_id)

    return ordered


def build_validation_manifest(
    root_task: str,
    *,
    project_root: Optional[Path] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a validation bundle manifest for a task hierarchy."""
    project_root = project_root or PathResolver.resolve_project_root()

    task_repo = TaskRepository(project_root=project_root)
    qa_repo = QARepository(project_root=project_root)

    index = TaskIndex(project_root=project_root)
    graph = index.get_task_graph(session_id=session_id)
    cluster_ids = _cluster_task_ids(str(root_task), graph=graph)

    tasks_payload: List[Dict[str, Any]] = []
    for task_id in cluster_ids:
        summary = graph.tasks.get(task_id)
        children: List[str] = []
        if summary:
            children.extend([str(c) for c in (summary.child_ids or []) if c])
        children.extend([str(c) for c in graph.get_children(task_id) if c])
        # Stable + unique.
        children = sorted({c for c in children if c and c != task_id})

        task_path = ""
        task_status = "missing"
        try:
            p = task_repo.get_path(task_id)
            task_path = str(p)
            task_status = p.parent.name
        except FileNotFoundError:
            pass

        qa_id = f"{task_id}-qa"
        qa_path = ""
        qa_status = "missing"
        try:
            qp = qa_repo.get_path(qa_id)
            qa_path = str(qp)
            qa_status = qp.parent.name
        except FileNotFoundError:
            pass

        evidence_dir = str(EvidenceService(task_id, project_root=project_root).get_evidence_root())

        tasks_payload.append(
            {
                "taskId": task_id,
                "taskStatus": task_status,
                "taskPath": task_path,
                "qaId": qa_id,
                "qaStatus": qa_status,
                "qaPath": qa_path,
                "children": children,
                "evidenceDir": evidence_dir,
            }
        )

    manifest: Dict[str, Any] = {
        "rootTask": str(root_task),
        "generatedAt": utc_timestamp(),
        "tasks": tasks_payload,
    }
    if session_id:
        manifest["sessionId"] = str(session_id)

    return manifest


__all__ = ["build_validation_manifest"]
