"""Tracking helpers for evidence rounds.

This module implements the core logic behind `edison session track …`:
- Ensures the correct evidence round directory exists
- Writes/updates tracking metadata in the round's reports

Design goals:
- Use EvidenceService for all evidence I/O (single source of truth)
- Avoid hardcoded filesystem paths
- Keep CLI as a thin wrapper over this module
"""
from __future__ import annotations

import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.tracking.liveness import is_stale, pid_is_running
from edison.core.utils.time import utc_timestamp
from edison.core.tracking.process_events import append_process_event

from .service import EvidenceService
from . import rounds


def _pid() -> int:
    return int(os.getpid())

def _launcher_fields() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "launcherKind": "edison-cli",
        "launcherPid": int(os.getpid()),
        "parentPid": int(os.getppid()),
    }
    sid = str(os.environ.get("AGENTS_SESSION") or "").strip()
    if sid:
        payload["sessionId"] = sid
    return payload


_VALIDATOR_PREFIX = "validator-"
_VALIDATOR_REPORT_SUFFIX = "-report"


def _validator_id_from_path(path: Path) -> str:
    stem = path.stem  # validator-<id>-report
    if stem.startswith(_VALIDATOR_PREFIX):
        stem = stem[len(_VALIDATOR_PREFIX) :]
    if stem.endswith(_VALIDATOR_REPORT_SUFFIX):
        stem = stem[: -len(_VALIDATOR_REPORT_SUFFIX)]
    return stem


def _run_id(existing: Any = None, *, requested: str | None = None) -> str:
    """Return a stable run id for a tracking payload."""
    rid = str(requested or "").strip()
    if rid:
        return rid
    rid = str((existing or {}).get("runId") or "").strip() if isinstance(existing, dict) else ""
    if rid:
        return rid
    return str(uuid.uuid4())


def _tracking_payload(
    *,
    run_id: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    continuation_id: str | None = None,
    last_active: str | None = None,
    process_id: int | None = None,
    existing: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    now = utc_timestamp()
    rid = _run_id(existing, requested=run_id)
    payload: Dict[str, Any] = {
        "runId": rid,
        "processId": int(process_id) if process_id is not None else _pid(),
        "hostname": socket.gethostname(),
        "startedAt": started_at or now,
        "lastActive": last_active or now,
    }
    completed = str(completed_at or "").strip()
    if completed:
        payload["completedAt"] = completed
    if continuation_id:
        payload["continuationId"] = continuation_id
    return payload


def _round_for_new_implementation(ev: EvidenceService) -> int:
    current = ev.get_current_round()
    if current is None:
        return 1
    data = ev.read_implementation_report(round_num=current)
    status = str((data or {}).get("completionStatus") or "").strip().lower()
    if status in {"complete", "blocked"}:
        return current + 1
    return current


def start_implementation(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    model: Optional[str] = None,
    round_num: Optional[int] = None,
    implementation_approach: str = "orchestrator-direct",
    continuation_id: Optional[str] = None,
    run_id: Optional[str] = None,
    process_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Start (or resume) tracking for an implementation round."""
    ev = EvidenceService(task_id, project_root=project_root)
    resolved_round = int(round_num) if round_num is not None else _round_for_new_implementation(ev)
    if resolved_round < 1:
        raise ValueError("round_num must be >= 1")
    round_dir = ev.ensure_round(resolved_round)
    ev.update_metadata(round_num=resolved_round)

    report_path = round_dir / ev.implementation_filename
    existing = ev.read_implementation_report(round_num=resolved_round)
    report: Dict[str, Any] = existing if isinstance(existing, dict) else {}

    report.setdefault("taskId", task_id)
    report.setdefault("round", int(resolved_round))
    report.setdefault("implementationApproach", implementation_approach)
    report.setdefault("primaryModel", model or "unknown")
    report.setdefault("completionStatus", "partial")
    report.setdefault("followUpTasks", [])
    report.setdefault("notesForValidator", "")

    tracking = report.get("tracking") if isinstance(report.get("tracking"), dict) else {}
    report["tracking"] = _tracking_payload(
        run_id=run_id,
        started_at=str(tracking.get("startedAt") or "") or None,
        continuation_id=continuation_id or (tracking.get("continuationId") if tracking else None),
        last_active=None,
        process_id=process_id,
        existing=tracking,
    )

    ev.write_implementation_report(report, round_num=resolved_round)

    tr = report.get("tracking") if isinstance(report.get("tracking"), dict) else {}
    append_process_event(
        "process.started",
        repo_root=project_root,
        run_id=str(tr.get("runId") or "") or None,
        kind="implementation",
        taskId=task_id,
        round=int(resolved_round),
        model=report.get("primaryModel"),
        processId=tr.get("processId"),
        processHostname=tr.get("hostname"),
        startedAt=tr.get("startedAt"),
        lastActive=tr.get("lastActive"),
        continuationId=tr.get("continuationId"),
        **_launcher_fields(),
    )

    return {
        "taskId": task_id,
        "type": "implementation",
        "round": int(resolved_round),
        "path": str(report_path),
        "runId": tr.get("runId"),
        "processId": tr.get("processId"),
    }


def start_validation(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    validator_id: str,
    model: str,
    round_num: Optional[int] = None,
    zen_role: Optional[str] = None,
    continuation_id: Optional[str] = None,
    run_id: Optional[str] = None,
    process_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Start tracking for a validator execution by writing a pending report."""
    ev = EvidenceService(task_id, project_root=project_root)
    resolved_round = int(round_num or ev.get_current_round() or 1)
    round_dir = ev.ensure_round(resolved_round)
    ev.update_metadata(round_num=resolved_round)

    report_path = ev.get_validator_report_path(round_dir, validator_id)
    existing = ev.read_validator_report(validator_id, round_num=resolved_round)
    report: Dict[str, Any] = existing if isinstance(existing, dict) else {}

    report.setdefault("taskId", task_id)
    report.setdefault("round", int(resolved_round))
    report.setdefault("validatorId", str(validator_id))
    report.setdefault("model", str(model))
    report.setdefault("zenRole", zen_role)
    report.setdefault("verdict", "pending")
    report.setdefault("findings", [])
    report.setdefault("strengths", [])
    report.setdefault("evidenceReviewed", [])
    report.setdefault("summary", "")
    report.setdefault("followUpTasks", [])

    tracking = report.get("tracking") if isinstance(report.get("tracking"), dict) else {}
    report["tracking"] = _tracking_payload(
        run_id=run_id,
        started_at=str(tracking.get("startedAt") or "") or None,
        continuation_id=continuation_id or (tracking.get("continuationId") if tracking else None),
        last_active=None,
        process_id=process_id,
        existing=tracking,
    )

    ev.write_validator_report(validator_id, report, round_num=resolved_round)

    tr = report.get("tracking") if isinstance(report.get("tracking"), dict) else {}
    append_process_event(
        "process.started",
        repo_root=project_root,
        run_id=str(tr.get("runId") or "") or None,
        kind="validation",
        taskId=task_id,
        round=int(resolved_round),
        validatorId=str(validator_id),
        model=str(model),
        processId=tr.get("processId"),
        processHostname=tr.get("hostname"),
        startedAt=tr.get("startedAt"),
        lastActive=tr.get("lastActive"),
        continuationId=tr.get("continuationId"),
        zenRole=report.get("zenRole"),
        **_launcher_fields(),
    )

    return {
        "taskId": task_id,
        "type": "validation",
        "round": int(resolved_round),
        "validatorId": str(validator_id),
        "path": str(report_path),
        "runId": tr.get("runId"),
        "processId": tr.get("processId"),
    }

def heartbeat(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    validator_id: str | None = None,
    run_id: str | None = None,
    round_num: int | None = None,
    process_id: int | None = None,
) -> Dict[str, Any]:
    """Update lastActive for tracking records in the current round.

    Note: CLI invocations are separate processes, so heartbeats must not require
    PID affinity. We update any present tracking payloads for the task's current
    round and fail closed only when no tracking records exist at all.
    """
    ev = EvidenceService(task_id, project_root=project_root)
    resolved_round = int(round_num or ev.get_current_round() or 1)
    round_dir = ev.ensure_round(resolved_round)

    updated: List[str] = []
    updated_records: List[Dict[str, Any]] = []
    now = utc_timestamp()

    requested_run = str(run_id or "").strip()
    requested_validator = str(validator_id or "").strip()

    # Implementation report (if present)
    if not requested_validator:
        impl = ev.read_implementation_report(round_num=resolved_round)
        if isinstance(impl, dict):
            tracking = impl.get("tracking")
            if isinstance(tracking, dict):
                if requested_run and str(tracking.get("runId") or "").strip() != requested_run:
                    pass
                else:
                    tracking["lastActive"] = now
                    if process_id is not None:
                        tracking["processId"] = int(process_id)
                    impl["tracking"] = tracking
                    ev.write_implementation_report(impl, round_num=resolved_round)
                    updated.append(str(round_dir / ev.implementation_filename))
                    updated_records.append(
                        {
                            "type": "implementation",
                            "taskId": task_id,
                            "round": int(resolved_round),
                            "runId": tracking.get("runId"),
                            "processId": tracking.get("processId"),
                            "lastActive": tracking.get("lastActive"),
                        }
                    )
                    append_process_event(
                        "process.heartbeat",
                        repo_root=project_root,
                        run_id=str(tracking.get("runId") or "") or None,
                        kind="implementation",
                        taskId=task_id,
                        round=int(resolved_round),
                        model=impl.get("primaryModel"),
                        processId=tracking.get("processId"),
                        processHostname=tracking.get("hostname"),
                        lastActive=tracking.get("lastActive"),
                        **_launcher_fields(),
                    )

    # Validator reports in this round (if present)
    for p in ev.list_validator_reports(round_num=resolved_round):
        try:
            vid = _validator_id_from_path(p)
            if requested_validator and vid != requested_validator:
                continue
            data = ev.read_validator_report(vid, round_num=resolved_round)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        tr = data.get("tracking")
        if isinstance(tr, dict):
            if requested_run and str(tr.get("runId") or "").strip() != requested_run:
                continue
            tr["lastActive"] = now
            if process_id is not None:
                tr["processId"] = int(process_id)
            data["tracking"] = tr
            # p.stem is "validator-<id>-report" but EvidenceService accepts either.
            ev.write_validator_report(vid, data, round_num=resolved_round)
            updated.append(str(p))
            updated_records.append(
                {
                    "type": "validation",
                    "taskId": task_id,
                    "round": int(resolved_round),
                    "validatorId": data.get("validatorId"),
                    "runId": tr.get("runId"),
                    "processId": tr.get("processId"),
                    "lastActive": tr.get("lastActive"),
                }
            )
            append_process_event(
                "process.heartbeat",
                repo_root=project_root,
                run_id=str(tr.get("runId") or "") or None,
                kind="validation",
                taskId=task_id,
                round=int(resolved_round),
                validatorId=data.get("validatorId"),
                model=data.get("model"),
                processId=tr.get("processId"),
                processHostname=tr.get("hostname"),
                lastActive=tr.get("lastActive"),
                zenRole=data.get("zenRole"),
                **_launcher_fields(),
            )

    if not updated:
        raise RuntimeError("No tracking records found for this process")

    return {
        "taskId": task_id,
        "round": int(resolved_round),
        "updated": updated,
        "heartbeatAt": now,
        "updatedRecords": updated_records,
    }


def complete_validation(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    validator_id: str,
    round_num: int | None = None,
    run_id: str | None = None,
    process_id: int | None = None,
) -> Dict[str, Any]:
    """Mark tracking complete for a single validator in a round."""
    ev = EvidenceService(task_id, project_root=project_root)
    resolved_round = int(round_num or ev.get_current_round() or 1)
    round_dir = ev.ensure_round(resolved_round)

    report_path = ev.get_validator_report_path(round_dir, validator_id)
    data = ev.read_validator_report(validator_id, round_num=resolved_round)
    if not isinstance(data, dict):
        raise RuntimeError(f"No validator report found for '{validator_id}' in round {resolved_round}")

    tr = data.get("tracking")
    if not isinstance(tr, dict):
        raise RuntimeError(f"No tracking payload found for '{validator_id}' in round {resolved_round}")

    requested_run = str(run_id or "").strip()
    if requested_run and str(tr.get("runId") or "").strip() != requested_run:
        raise RuntimeError(f"runId mismatch for '{validator_id}' in round {resolved_round}")

    now = utc_timestamp(repo_root=project_root)
    tr["lastActive"] = now
    tr["completedAt"] = now
    if process_id is not None:
        tr["processId"] = int(process_id)
    data["tracking"] = tr
    ev.write_validator_report(validator_id, data, round_num=resolved_round)

    append_process_event(
        "process.completed",
        repo_root=project_root,
        run_id=str(tr.get("runId") or "") or None,
        kind="validation",
        taskId=task_id,
        round=int(resolved_round),
        validatorId=data.get("validatorId"),
        model=data.get("model"),
        processId=tr.get("processId"),
        processHostname=tr.get("hostname"),
        completedAt=tr.get("completedAt"),
        lastActive=tr.get("lastActive"),
        zenRole=data.get("zenRole"),
        **_launcher_fields(),
    )

    return {
        "taskId": task_id,
        "type": "validation",
        "validatorId": str(validator_id),
        "round": int(resolved_round),
        "path": str(report_path),
        "runId": tr.get("runId"),
        "processId": tr.get("processId"),
        "completedAt": tr.get("completedAt"),
    }


def complete(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    implementation_status: str = "complete",
    run_id: str | None = None,
    process_id: int | None = None,
) -> Dict[str, Any]:
    """Mark tracking complete for the current round.

    Note: CLI invocations are separate processes, so completion must not require
    PID affinity. We mark completion for any tracking payloads present in the
    task's current round.
    """
    ev = EvidenceService(task_id, project_root=project_root)
    round_num = int(ev.get_current_round() or 1)
    round_dir = ev.ensure_round(round_num)

    updated: List[str] = []
    now = utc_timestamp()

    impl = ev.read_implementation_report(round_num=round_num)
    if isinstance(impl, dict):
        tr = impl.get("tracking")
        if isinstance(tr, dict):
            requested_run = str(run_id or "").strip()
            if requested_run and str(tr.get("runId") or "").strip() != requested_run:
                raise RuntimeError("runId mismatch for implementation tracking")
            tr["lastActive"] = now
            tr["completedAt"] = now
            if process_id is not None:
                tr["processId"] = int(process_id)
            impl["tracking"] = tr
            # Track completion also stamps completionStatus by default.
            impl["completionStatus"] = str(implementation_status)
            ev.write_implementation_report(impl, round_num=round_num)
            updated.append(str(round_dir / ev.implementation_filename))
            append_process_event(
                "process.completed",
                repo_root=project_root,
                run_id=str(tr.get("runId") or "") or None,
                kind="implementation",
                taskId=task_id,
                round=int(round_num),
                model=impl.get("primaryModel"),
                processId=tr.get("processId"),
                processHostname=tr.get("hostname"),
                completedAt=tr.get("completedAt"),
                lastActive=tr.get("lastActive"),
                **_launcher_fields(),
            )

    if not updated:
        raise RuntimeError("No tracking records found for this round")

    return {"taskId": task_id, "round": round_num, "updated": updated, "completedAt": now}


def list_active(*, project_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all active (in-progress) tracking records under the evidence tree."""
    from edison.core.qa._utils import get_evidence_base_path
    from edison.core.tracking.process_events import list_processes as list_tracked_processes

    base = get_evidence_base_path(project_root)
    if not base.exists():
        return []

    proc_index: Dict[str, Dict[str, Any]] = {}
    try:
        proc_index = {
            str(p.get("runId") or ""): p
            for p in list_tracked_processes(repo_root=project_root, active_only=False, update_stop_events=True)
            if str(p.get("runId") or "").strip()
        }
    except Exception:
        proc_index = {}

    out: List[Dict[str, Any]] = []
    for task_dir in sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.name):
        latest = rounds.find_latest_round_dir(task_dir)
        if latest is None:
            continue
        try:
            round_num = rounds.get_round_number(latest)
        except Exception:
            continue

        ev = EvidenceService(task_dir.name, project_root=project_root)

        # Implementation report
        impl = ev.read_implementation_report(round_num=round_num)
        if isinstance(impl, dict) and str(impl.get("completionStatus") or "").strip().lower() == "partial":
            tr = impl.get("tracking") if isinstance(impl.get("tracking"), dict) else {}
            item: Dict[str, Any] = {
                "taskId": task_dir.name,
                "type": "implementation",
                "round": int(round_num),
                "runId": tr.get("runId"),
                "processId": tr.get("processId"),
                "hostname": tr.get("hostname"),
                "model": impl.get("primaryModel"),
                "startedAt": tr.get("startedAt"),
                "lastActive": tr.get("lastActive"),
                "path": str(latest / ev.implementation_filename),
            }
            if tr.get("continuationId"):
                item["continuationId"] = tr.get("continuationId")
            idx = proc_index.get(str(item.get("runId") or "").strip())
            if isinstance(idx, dict):
                item["isRunning"] = idx.get("isRunning")
                item["isStale"] = idx.get("isStale")
                item["state"] = idx.get("state")
                item["processEvent"] = idx.get("event")
            else:
                item["isRunning"] = pid_is_running(process_id=item.get("processId"), hostname=item.get("hostname"))
                item["isStale"] = is_stale(repo_root=project_root, last_active=item.get("lastActive"))
            out.append(item)

        # Validator reports
        for p in ev.list_validator_reports(round_num=round_num):
            vid = _validator_id_from_path(p)
            data = ev.read_validator_report(vid, round_num=round_num)
            if not isinstance(data, dict):
                continue
            if str(data.get("verdict") or "").strip().lower() != "pending":
                continue
            tr = data.get("tracking") if isinstance(data.get("tracking"), dict) else {}
            item: Dict[str, Any] = {
                "taskId": task_dir.name,
                "type": "validation",
                "validatorId": data.get("validatorId"),
                "round": int(round_num),
                "runId": tr.get("runId"),
                "processId": tr.get("processId"),
                "hostname": tr.get("hostname"),
                "model": data.get("model"),
                "startedAt": tr.get("startedAt"),
                "lastActive": tr.get("lastActive"),
                "path": str(p),
            }
            if tr.get("continuationId"):
                item["continuationId"] = tr.get("continuationId")
            idx = proc_index.get(str(item.get("runId") or "").strip())
            if isinstance(idx, dict):
                item["isRunning"] = idx.get("isRunning")
                item["isStale"] = idx.get("isStale")
                item["state"] = idx.get("state")
                item["processEvent"] = idx.get("event")
            else:
                item["isRunning"] = pid_is_running(process_id=item.get("processId"), hostname=item.get("hostname"))
                item["isStale"] = is_stale(repo_root=project_root, last_active=item.get("lastActive"))
            out.append(item)

    return out


__all__ = [
    "start_implementation",
    "start_validation",
    "heartbeat",
    "complete_validation",
    "complete",
    "list_active",
]
