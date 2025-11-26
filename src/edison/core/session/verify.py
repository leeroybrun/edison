#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from edison.core.session.next import compute_next
from edison.core.session import manager as session_manager
from edison.core.session import store as session_store
from edison.core.session.context import SessionContext
from edison.core import task  # type: ignore
from edison.core.file_io.utils import read_json_safe as io_read_json_safe, utc_timestamp as io_utc_timestamp 
from edison.core.qa import evidence as qa_evidence 
from edison.core.utils import cli 
def _latest_round_dir(task_id: str) -> Path | None:
    """Return the latest evidence round directory for ``task_id``."""
    ev_root = qa_evidence.get_evidence_dir(task_id)
    latest_round = qa_evidence.get_latest_round(task_id)
    if latest_round is None:
        return None
    return ev_root / f"round-{latest_round}"


def verify_session_health(session_id: str) -> dict:
    session_id = session_store.normalize_session_id(session_id)
    with SessionContext.in_session_worktree(session_id):
        session = session_manager.get_session(session_id)

    failures: list[str] = []
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
    # Detect manual moves: metadata status must match directory status
    for task_id in session.get("tasks", {}):
        try:
            p = task.find_record(task_id, "task")
            meta = task.read_metadata(p, "task")
            dir_status = p.parent.name
            if meta.status and meta.status != dir_status:
                msg = f"Task {task_id} metadata status '{meta.status}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "task", "taskId": task_id, "meta": meta.status, "dir": dir_status})
        except FileNotFoundError:
            msg = f"Task {task_id} missing on disk"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "task", "taskId": task_id, "state": "missing"})
    for qa_id, qa in session.get("qa", {}).items():
        task_id = qa.get("taskId") if isinstance(qa, dict) else qa_id.rstrip("-qa")
        try:
            p = task.find_record(task_id, "qa")
            meta = task.read_metadata(p, "qa")
            dir_status = p.parent.name
            if meta.status and meta.status != dir_status:
                msg = f"QA {qa_id} metadata status '{meta.status}' != directory '{dir_status}' (no manual moves)"
                failures.append(msg)
                health["categories"]["stateMismatches"].append({"type": "qa", "qaId": qa_id, "meta": meta.status, "dir": dir_status})
        except FileNotFoundError:
            msg = f"QA {qa_id} missing on disk"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "qa", "qaId": qa_id, "state": "missing"})
    for task_id in session.get("tasks", {}):
        try:
            p = task.find_record(task_id, "task")
            status = p.parent.name
        except FileNotFoundError:
            msg = f"Task {task_id} missing on disk"
            failures.append(msg)
            continue
        if status not in {"done", "validated", "wip"}:
            msg = f"Task {task_id} unexpected state: {status}"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "task", "taskId": task_id, "state": status})

    for qa_id, qa in session.get("qa", {}).items():
        task_id = qa.get("taskId") if isinstance(qa, dict) else qa_id.rstrip("-qa")
        try:
            p = task.find_record(task_id, "qa")
            status = p.parent.name
        except FileNotFoundError:
            status = "missing"
        if status not in {"waiting", "todo", "wip", "done", "validated"}:
            msg = f"QA {qa_id} unexpected state: {status}"
            failures.append(msg)
            health["categories"]["unexpectedStates"].append({"type": "qa", "qaId": qa_id, "state": status})

    # New guard: every task in tasks/done MUST have QA in qa/done|validated and bundle-approved.json approved=true
    for task_id, task_entry in session.get("tasks", {}).items():
        try:
            tpath = task.find_record(task_id, "task")
        except FileNotFoundError:
            continue
        if tpath.parent.name == "done":
            # QA must be done/validated
            try:
                qpath = task.find_record(task_id, "qa")
                qstate = qpath.parent.name
            except FileNotFoundError:
                qpath = None
                qstate = "missing"
            if qstate not in {"done", "validated"}:
                msg = f"Task {task_id} is in tasks/done but QA is not done/validated (found {qstate})"
                failures.append(msg)
                health["categories"]["missingQA"].append({"taskId": task_id, "qaState": qstate})
            # bundle-approved.json must exist and approved=true
            latest = _latest_round_dir(task_id)
            if not latest or not (latest / "bundle-approved.json").exists():
                msg = f"Task {task_id} missing bundle-approved.json in latest round"
                failures.append(msg)
                health["categories"]["missingEvidence"].append({"taskId": task_id, "file": "bundle-approved.json"})
            else:
                try:
                    data = io_read_json_safe(latest / "bundle-approved.json")
                except Exception as err:
                    msg = f"Task {task_id} invalid bundle-approved.json: {err}"
                    failures.append(msg)
                    health["categories"]["bundleNotApproved"].append({"taskId": task_id, "reason": "invalid_json"})
                else:
                    if not data.get("approved"):
                        msg = f"Task {task_id} bundle-approved.json indicates not approved"
                        failures.append(msg)
                        health["categories"]["bundleNotApproved"].append({"taskId": task_id, "reason": "not_approved"})

    plan = compute_next(session_id, scope="session", limit=0)
    if plan.get("blockers") or plan.get("reportsMissing"):
        failures.append("Unresolved blockers or missing reports remain; resolve automation/evidence before closing.")
        health["categories"]["blockersOrReportsMissing"] = True

    if failures:
        health["ok"] = False
        return health

    # On success, mark session moving into the closing phase and persist
    session["state"] = "closing"
    # Keep filesystem layout (sessions/wip) but update metadata timestamps
    session.setdefault("meta", {})["lastActive"] = io_utc_timestamp()
    session_store.save_session(session_id, session)

    return health


def _apply_repo_root(repo_root: Path | None) -> None:
    if repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(repo_root)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verify session for phase guards")
    cli.parse_common_args(parser)
    parser.add_argument("session_id")
    parser.add_argument("--phase", required=True, choices=["closing"])
    args = parser.parse_args(argv)

    _apply_repo_root(args.repo_root)

    health = verify_session_health(args.session_id)

    if args.json:
        print(cli.output_json(health))
    else:
        if health.get("ok"):
            cli.success("Session passes closing verification")
        else:
            cli.error("Session verification failed")

    return 0 if health.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
