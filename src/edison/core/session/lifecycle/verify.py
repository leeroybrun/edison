#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.session.lifecycle import manager as session_manager
from edison.core.session.core.id import validate_session_id
from edison.core.session.core.context import SessionContext
from edison.core.session import persistence as graph
from edison.core.task import TaskRepository
from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.utils.io import read_json as io_read_json
from edison.core.utils.time import utc_timestamp as io_utc_timestamp
from edison.core.qa import evidence as qa_evidence
from edison.core.utils.cli.arguments import parse_common_args
from edison.core.utils.cli.output import output_json, error, success

if TYPE_CHECKING:
    from edison.core.qa.workflow.repository import QARepository


def _latest_round_dir(task_id: str) -> Optional[Path]:
    """Return the latest evidence round directory for ``task_id``.
    
    Uses EvidenceService.get_current_round_dir() as single source.
    """
    ev_svc = qa_evidence.EvidenceService(task_id)
    return ev_svc.get_current_round_dir()


def verify_session_health(session_id: str) -> Dict[str, Any]:
    # Lazy import to avoid circular dependency
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.session.next import compute_next

    session_id = validate_session_id(session_id)
    with SessionContext.in_session_worktree(session_id):
        session = session_manager.get_session(session_id)

    failures: List[str] = []
    health = {
        "ok": True,
        "sessionId": session_id,
        "categories": {
            "stateMismatches": [],
            "unexpectedStates": [],
            "missingQA": [],
            "missingEvidence": [],
            "bundleNotApproved": [],
            "blockersOrReportsMissing": False,
        },
        "details": [],
    }
    # Detect manual moves: entity state must match directory status
    # Use TaskRepository to get tasks belonging to this session (task files are source of truth)
    task_repo = TaskRepository()
    qa_repo = QARepository()
    
    # Get tasks from TaskRepository instead of session JSON
    session_tasks = task_repo.find_by_session(session_id)
    session_task_ids = {t.id for t in session_tasks}
    
    for task in session_tasks:
        task_id = task.id
        try:
            p = task_repo.get_path(task_id)
            dir_status = p.parent.name
            entity_state = task.state
            if entity_state and entity_state != dir_status:
                msg = f"Task {task_id} entity state '{entity_state}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "task", "taskId": task_id, "meta": entity_state, "dir": dir_status})
        except FileNotFoundError:
            msg = f"Task {task_id} missing on disk"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "task", "taskId": task_id, "state": "missing"})
    # Verify QA records for tasks in this session (QA tied to task via task_id)
    for task_id in session_task_ids:
        qa_id = f"{task_id}-qa"
        try:
            p = qa_repo.get_path(qa_id)
            entity = qa_repo.get(qa_id)
            dir_status = p.parent.name
            entity_state = entity.state if entity else None
            if entity_state and entity_state != dir_status:
                msg = f"QA {qa_id} entity state '{entity_state}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "qa", "qaId": qa_id, "meta": entity_state, "dir": dir_status})
        except FileNotFoundError:
            # QA might not exist for all tasks (optional)
            pass
    for task_id in session_task_ids:
        try:
            p = task_repo.get_path(task_id)
            status = p.parent.name
        except FileNotFoundError:
            msg = f"Task {task_id} missing on disk"
            failures.append(msg)
            continue
        if status not in WorkflowConfig().task_states:
            msg = f"Task {task_id} unexpected state: {status}"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "task", "taskId": task_id, "state": status})

    # Check QA state for each task in the session (QA is tied to tasks)
    for task_id in session_task_ids:
        qa_id = f"{task_id}-qa"
        try:
            p = qa_repo.get_path(qa_id)
            status = p.parent.name
        except FileNotFoundError:
            status = "missing"
        if status not in WorkflowConfig().qa_states and status != "missing":
            msg = f"QA {qa_id} unexpected state: {status}"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "qa", "qaId": qa_id, "state": status})

    # New guard: every task in tasks/done MUST have QA in qa/done|validated and bundle approval marker approved=true
    # Get state names from config
    task_done = WorkflowConfig().get_semantic_state("task", "done")
    qa_done = WorkflowConfig().get_semantic_state("qa", "done")
    qa_validated = WorkflowConfig().get_semantic_state("qa", "validated")
    qa_ready_states = {qa_done, qa_validated}
    
    for task in session_tasks:
        task_id = task.id
        try:
            tpath = task_repo.get_path(task_id)
        except FileNotFoundError:
            continue
        if tpath.parent.name == task_done:
            # QA must be done/validated
            try:
                qpath = qa_repo.get_path(f"{task_id}-qa")
                qstate = qpath.parent.name
            except FileNotFoundError:
                qpath = None
                qstate = "missing"
            if qstate not in qa_ready_states:
                msg = f"Task {task_id} is in tasks/done but QA is not done/validated (found {qstate})"
                failures.append(msg)
                health["categories"]["missingQA"].append({"taskId": task_id, "qaState": qstate})
            # Bundle must exist and be approved - use EvidenceService (single source)
            ev_svc = qa_evidence.EvidenceService(task_id)
            bundle_filename = ev_svc.bundle_filename
            bundle_data = ev_svc.read_bundle()
            
            if not bundle_data:
                msg = f"Task {task_id} missing {bundle_filename} in latest round"
                failures.append(msg)
                health["categories"]["missingEvidence"].append({"taskId": task_id, "file": bundle_filename})
            elif not bundle_data.get("approved"):
                msg = f"Task {task_id} {bundle_filename} indicates not approved"
                failures.append(msg)
                health["categories"]["bundleNotApproved"].append({"taskId": task_id, "reason": "not_approved"})

    plan = compute_next(session_id, scope="session", limit=0)
    if plan.get("blockers") or plan.get("reportsMissing"):
        failures.append("Unresolved blockers or missing reports remain; resolve automation/evidence before closing.")
        health["categories"]["blockersOrReportsMissing"] = True
        for blocker in plan.get("blockers") or []:
            health["details"].append({"kind": "blocker", "blocker": blocker})
        for report in plan.get("reportsMissing") or []:
            health["details"].append({"kind": "reportsMissing", "report": report})

    if failures:
        health["ok"] = False
        return health

    # Restore session-scoped records back to global queues before closing.
    #
    # This is part of the session lifecycle contract: the session tree provides isolation
    # while active, and on close-out we restore all session-owned records to the global
    # queues transactionally (FAIL-CLOSED on restore errors).
    try:
        from edison.core.session.lifecycle.recovery import restore_records_to_global_transactional

        restore_records_to_global_transactional(session_id)
    except Exception as e:
        health["ok"] = False
        health["details"].append(f"Restore to global queues failed: {e}")
        return health

    # On success, transition session to closing using the canonical repository API.
    from edison.core.session.persistence.repository import SessionRepository

    closing_state = WorkflowConfig().get_semantic_state("session", "closing")
    session_repo = SessionRepository()
    try:
        entity = session_repo.get_or_raise(session_id)
        session_repo.transition(
            session_id,
            closing_state,
            context={
                "session_id": session_id,
                "session": entity.to_dict(),
                "entity_type": "session",
                "entity_id": session_id,
            },
            reason="session-verify",
        )
    except Exception as e:
        health["ok"] = False
        health["details"].append(f"Transition to closing blocked: {e}")
        return health

    return health


def _apply_repo_root(repo_root: Optional[Path]) -> None:
    if repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(repo_root)


def main(argv: Optional[List[str]] = None) -> int:

    parser = argparse.ArgumentParser(description="Verify session for phase guards")
    parse_common_args(parser)
    parser.add_argument("session_id")
    parser.add_argument("--phase", required=True, choices=["closing"])
    args = parser.parse_args(argv)

    _apply_repo_root(args.repo_root)

    health = verify_session_health(args.session_id)

    if args.json:
        print(output_json(health))
    else:
        if health.get("ok"):
            success("Session passes closing verification")
        else:
            error("Session verification failed")

    return 0 if health.get("ok") else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
