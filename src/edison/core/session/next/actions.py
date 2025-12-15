"""Action generation and helper functions for session next computation.

Functions for building action recommendations and related task discovery.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from edison.core.qa.evidence import (
    EvidenceService,
    load_bundle_followups,  # noqa: F401 - re-exported for compute.py
    load_impl_followups,  # noqa: F401 - re-exported for compute.py
    missing_evidence_blockers,  # noqa: F401 - re-exported for compute.py
    read_validator_reports,  # noqa: F401 - re-exported for compute.py
)
from edison.core.session.next.utils import project_cfg_dir
from edison.core.task import TaskRepository, safe_relative
from edison.core.utils.io import read_json as io_read_json
from edison.core.utils.patterns import matches_any_pattern

if TYPE_CHECKING:
    pass


def infer_task_status(task_id: str) -> str:
    """Infer task status from filesystem location."""
    try:
        task_repo = TaskRepository()
        p = task_repo.get_path(task_id)
        return p.parent.name or "unknown"
    except FileNotFoundError:
        return "missing"


def infer_qa_status(task_id: str) -> str:
    """Infer QA status from filesystem location."""
    # Lazy import to avoid circular dependency
    from edison.core.qa.workflow.repository import QARepository
    try:
        qa_repo = QARepository()
        p = qa_repo.get_path(f"{task_id}-qa")
        return p.parent.name or "missing"
    except FileNotFoundError:
        return "missing"


def find_related_in_session(session_id: str, task_id: str) -> list[dict[str, Any]]:
    """Find related tasks/QAs in session: parent, children, linked tasks.

    Uses TaskRepository (task files) as the single source of truth for relationships.
    Session ID is used to filter tasks to the session context.
    """
    task_repo = TaskRepository()
    
    # Get the task to find its relationships
    task = task_repo.get(task_id)
    if not task:
        return []

    related = []

    # Parent task (from task.parent_id field in task file)
    if task.parent_id:
        parent_status = infer_task_status(task.parent_id)
        parent_qa = infer_qa_status(task.parent_id)
        related.append({
            "relationship": "parent",
            "taskId": task.parent_id,
            "taskStatus": parent_status,
            "qaStatus": parent_qa,
            "note": f"This task is a follow-up to {task.parent_id}",
        })

    # Child tasks (from task.child_ids field in task file)
    for child_id in task.child_ids:
        child_status = infer_task_status(child_id)
        child_qa = infer_qa_status(child_id)
        related.append({
            "relationship": "child",
            "taskId": child_id,
            "taskStatus": child_status,
            "qaStatus": child_qa,
            "note": f"Follow-up task spawned from {task_id}",
        })

    # Sibling tasks (other children of same parent)
    if task.parent_id:
        parent_task = task_repo.get(task.parent_id)
        if parent_task:
            for sibling_id in parent_task.child_ids:
                if sibling_id != task_id:
                    sib_status = infer_task_status(sibling_id)
                    sib_qa = infer_qa_status(sibling_id)
                    related.append({
                        "relationship": "sibling",
                        "taskId": sibling_id,
                        "taskStatus": sib_status,
                        "qaStatus": sib_qa,
                        "note": f"Sibling task (same parent {task.parent_id})",
                    })

    return related


def build_reports_missing(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Build reportsMissing list for visibility.

    Uses TaskRepository to find tasks in the session (by session_id).
    Task files are the single source of truth for task data.

    Args:
        session: Session dictionary (used to get session_id)

    Returns:
        List of missing report entries
    """
    from edison.core.config.domains.workflow import WorkflowConfig
    workflow_cfg = WorkflowConfig()

    # Get QA states from config
    qa_wip = workflow_cfg.get_semantic_state("qa", "wip")
    qa_todo = workflow_cfg.get_semantic_state("qa", "todo")
    qa_active_states = {qa_wip, qa_todo}

    reports_missing: list[dict[str, Any]] = []

    # Get tasks from TaskRepository instead of session JSON
    task_repo = TaskRepository()
    session_id = session.get("id") or session.get("meta", {}).get("sessionId")
    
    # Find tasks belonging to this session
    if session_id:
        session_tasks = task_repo.find_by_session(session_id)
    else:
        # Fallback: get all tasks (shouldn't happen in normal usage)
        session_tasks = task_repo.get_all()
    
    for task in session_tasks:
        task_id = task.id
        # Validator reports expected when QA is wip/todo
        qstat = infer_qa_status(task_id)
        if qstat in qa_active_states:
            v = read_validator_reports(task_id)
            have = {
                str(r.get("validatorId") or r.get("validator_id") or r.get("id") or "")
                for r in v.get("reports", [])
                if (r.get("validatorId") or r.get("validator_id") or r.get("id"))
            }
            # Derive expected blocking IDs from the canonical validator roster (trigger-aware)
            try:
                from edison.core.registries.validators import ValidatorRegistry

                registry = ValidatorRegistry()
                roster = registry.build_execution_roster(task_id, session_id=session_id)
                need_blocking = {
                    v["id"]
                    for v in (roster.get("alwaysRequired", []) + roster.get("triggeredBlocking", []))
                    if isinstance(v, dict) and v.get("id")
                }
                for vid in sorted(need_blocking):
                    if str(vid) not in have:
                        reports_missing.append({
                            "taskId": task_id,
                            "type": "validator",
                            "validatorId": vid,
                            "suggested": [
                                "(re)run validator wave and write report per schema",
                                f"edison qa validate {task_id} --execute",
                            ],
                        })
            except Exception:
                pass

        # Implementation Report required for ALL tasks
        try:
            ev_svc = EvidenceService(task_id)
            latest_round = ev_svc.get_current_round()
            if latest_round is not None:
                impl_data = ev_svc.read_implementation_report(latest_round)
                if not impl_data:  # Empty dict means report doesn't exist
                    # Use configured filename from EvidenceService
                    impl_filename = ev_svc.implementation_filename
                    impl_path = ev_svc.get_evidence_root() / f"round-{latest_round}" / impl_filename
                    rel_path = safe_relative(impl_path)
                    reports_missing.append({
                        "taskId": task_id,
                        "type": "implementation",
                        "path": rel_path,
                        "suggested": [
                            "Write Implementation Report (Markdown frontmatter) per schema",
                            f"Create or update: {rel_path}",
                        ],
                    })
        except Exception:
            pass

        # Context7 markers expected for validators that require Context7 for this task
        try:
            from edison.core.registries.validators import ValidatorRegistry

            registry = ValidatorRegistry()
            roster = registry.build_execution_roster(task_id, session_id=session_id)
            validators_in_roster = (
                roster.get("alwaysRequired", [])
                + roster.get("triggeredBlocking", [])
                + roster.get("triggeredOptional", [])
            )
            required_pkgs: set[str] = set()
            for v in validators_in_roster:
                if not isinstance(v, dict):
                    continue
                if v.get("context7Required") and isinstance(v.get("context7Packages"), list):
                    required_pkgs |= {str(p) for p in v.get("context7Packages") if p}

            if required_pkgs:
                ev_svc_ctx7 = EvidenceService(task_id)
                latest_round_ctx7 = ev_svc_ctx7.get_current_round()
                latest = (
                    ev_svc_ctx7.get_evidence_root() / f"round-{latest_round_ctx7}"
                    if latest_round_ctx7 is not None
                    else None
                )
                missing_pkgs = sorted(
                    p
                    for p in required_pkgs
                    if not latest
                    or (
                        not (latest / f"context7-{p}.txt").exists()
                        and not (latest / f"context7-{p}.md").exists()
                    )
                )
                if missing_pkgs:
                    reports_missing.append(
                        {
                            "taskId": task_id,
                            "type": "context7",
                            "packages": missing_pkgs,
                            "suggested": [
                                "Write context7-<package>.txt in latest round with topics and doc references",
                                "Add a note in the task file documenting Context7 usage",
                            ],
                        }
                    )
        except Exception:
            pass

    return reports_missing
