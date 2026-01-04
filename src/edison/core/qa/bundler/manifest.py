"""Validation bundle manifest builder.

This module builds a cluster manifest for validation (task + QA + evidence dirs).

IMPORTANT:
- Hierarchy bundles (parent/child) and validation bundles (bundle_root) are distinct.
- Cluster selection is centralized in `edison.core.qa.bundler.cluster`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.time import utc_timestamp

from edison.core.task import TaskIndex, TaskRepository
from edison.core.qa.workflow.repository import QARepository
from edison.core.qa.evidence import EvidenceService
from edison.core.utils.paths import PathResolver
from edison.core.qa.bundler.cluster import select_cluster


def build_validation_manifest(
    root_task: str,
    *,
    scope: str | None = None,
    project_root: Optional[Path] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a validation bundle manifest for a task cluster."""
    project_root = project_root or PathResolver.resolve_project_root()

    task_repo = TaskRepository(project_root=project_root)
    qa_repo = QARepository(project_root=project_root)

    selection = select_cluster(str(root_task), scope=scope, project_root=project_root)

    index = TaskIndex(project_root=project_root)
    graph = index.get_task_graph(session_id=session_id)
    cluster_ids = list(selection.task_ids)

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
        "rootTask": str(selection.root_task_id),
        "scope": str(selection.scope.value),
        "generatedAt": utc_timestamp(),
        "tasks": tasks_payload,
    }
    if session_id:
        manifest["sessionId"] = str(session_id)

    return manifest


__all__ = ["build_validation_manifest"]
