#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.qa import evidence as qa_evidence
from edison.core.session.core.context import SessionContext
from edison.core.session.core.id import validate_session_id
from edison.core.session.lifecycle import manager as session_manager
from edison.core.task import TaskRepository
from edison.core.utils.cli.arguments import parse_common_args
from edison.core.utils.cli.output import error, output_json, success

if TYPE_CHECKING:  # pragma: no cover
    from edison.core.qa.workflow.repository import QARepository  # noqa: F401


def verify_session_health(session_id: str) -> dict[str, Any]:
    # Lazy import to avoid circular dependency
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.session.next import compute_next

    session_id = validate_session_id(session_id)
    with SessionContext.in_session_worktree(session_id):
        session_manager.get_session(session_id)

    failures: list[str] = []
    health: dict[str, Any] = {
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
            task_entity_state = task.state
            if task_entity_state and task_entity_state != dir_status:
                msg = f"Task {task_id} entity state '{task_entity_state}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "task", "taskId": task_id, "meta": task_entity_state, "dir": dir_status})
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
            qa_entity_state: str | None = entity.state if entity else None
            if qa_entity_state and qa_entity_state != dir_status:
                msg = f"QA {qa_id} entity state '{qa_entity_state}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "qa", "qaId": qa_id, "meta": qa_entity_state, "dir": dir_status})
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

    # Session-close evidence requirements (config-driven, fail-closed).
    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        qa_cfg = QAConfig()
        close_cfg = qa_cfg.validation_config.get("sessionClose", {}) if isinstance(qa_cfg.validation_config, dict) else {}
        required_close = close_cfg.get("requiredEvidenceFiles", []) if isinstance(close_cfg, dict) else []
        required_close = [str(x).strip() for x in (required_close or []) if str(x).strip()]

        if required_close:
            # For each required evidence file, accept success from any task in the session.
            missing_close: list[str] = []
            for filename in required_close:
                found_ok = False
                for task in session_tasks:
                    ev_svc = qa_evidence.EvidenceService(task.id)
                    rd = ev_svc.get_current_round_dir()
                    if rd is None:
                        continue
                    p = rd / filename
                    if not p.exists():
                        continue
                    parsed = parse_command_evidence(p)
                    if parsed is None:
                        continue
                    try:
                        if int(parsed.get("exitCode", 1)) == 0:
                            found_ok = True
                            break
                    except Exception:
                        continue
                if not found_ok:
                    missing_close.append(filename)

            if missing_close:
                # Deterministic suggestion: use the first task id in the session as the anchor.
                anchor = sorted([t.id for t in session_tasks if t and t.id])[:1]
                anchor_id = anchor[0] if anchor else "<task-id>"
                msg = (
                    "Session-close evidence missing: "
                    + ", ".join(missing_close)
                    + f". Capture + review session-close evidence (config-driven) using:\n  edison evidence init {anchor_id}\n  edison evidence capture {anchor_id} --session-close"
                )
                failures.append(msg)
                health["categories"]["missingEvidence"].append(
                    {"taskId": anchor_id, "file": ", ".join(missing_close), "kind": "sessionClose"}
                )
                health["details"].append(
                    {
                        "kind": "sessionCloseEvidence",
                        "missing": list(missing_close),
                        "suggested": [
                            f"edison evidence init {anchor_id}",
                            f"edison evidence capture {anchor_id} --session-close",
                            f"edison evidence show {anchor_id} --command <name>",
                            "Review evidence output and fix failures before closing.",
                        ],
                    }
                )
    except Exception:
        # Fail-open: session close evidence is additive; core state invariants and QA approval still apply.
        pass

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

    return health


def _apply_repo_root(repo_root: Path | None) -> None:
    if repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(repo_root)


def main(argv: list[str] | None = None) -> int:

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
