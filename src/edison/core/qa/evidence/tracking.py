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
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.time import utc_timestamp

from .service import EvidenceService
from . import rounds


def _pid() -> int:
    return int(os.getpid())


_VALIDATOR_PREFIX = "validator-"
_VALIDATOR_REPORT_SUFFIX = "-report"


def _validator_id_from_path(path: Path) -> str:
    stem = path.stem  # validator-<id>-report
    if stem.startswith(_VALIDATOR_PREFIX):
        stem = stem[len(_VALIDATOR_PREFIX) :]
    if stem.endswith(_VALIDATOR_REPORT_SUFFIX):
        stem = stem[: -len(_VALIDATOR_REPORT_SUFFIX)]
    return stem

def _tracking_payload(
    *,
    started_at: str | None = None,
    completed_at: str | None = None,
    continuation_id: str | None = None,
    last_active: str | None = None,
) -> Dict[str, Any]:
    now = utc_timestamp()
    return {
        "processId": _pid(),
        "hostname": socket.gethostname(),
        "startedAt": started_at or now,
        "lastActive": last_active or now,
        # Schemas currently require completedAt, so initialize it at start and
        # update it again on `complete`.
        "completedAt": completed_at or now,
        "continuationId": continuation_id,
    }


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
    implementation_approach: str = "orchestrator-direct",
    continuation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Start (or resume) tracking for an implementation round."""
    ev = EvidenceService(task_id, project_root=project_root)
    round_num = _round_for_new_implementation(ev)
    round_dir = ev.ensure_round(round_num)
    ev.update_metadata(round_num=round_num)

    report_path = round_dir / ev.implementation_filename
    existing = ev.read_implementation_report(round_num=round_num)
    report: Dict[str, Any] = existing if isinstance(existing, dict) else {}

    report.setdefault("taskId", task_id)
    report.setdefault("round", int(round_num))
    report.setdefault("implementationApproach", implementation_approach)
    report.setdefault("primaryModel", model or "unknown")
    report.setdefault("completionStatus", "partial")
    report.setdefault("followUpTasks", [])
    report.setdefault("notesForValidator", "")

    tracking = report.get("tracking") if isinstance(report.get("tracking"), dict) else {}
    report["tracking"] = _tracking_payload(
        started_at=str(tracking.get("startedAt") or "") or None,
        completed_at=str(tracking.get("completedAt") or "") or None,
        continuation_id=continuation_id or (tracking.get("continuationId") if tracking else None),
        last_active=None,
    )

    ev.write_implementation_report(report, round_num=round_num)

    return {
        "taskId": task_id,
        "type": "implementation",
        "round": int(round_num),
        "path": str(report_path),
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
        started_at=str(tracking.get("startedAt") or "") or None,
        completed_at=str(tracking.get("completedAt") or "") or None,
        continuation_id=continuation_id or (tracking.get("continuationId") if tracking else None),
        last_active=None,
    )

    ev.write_validator_report(validator_id, report, round_num=resolved_round)

    return {
        "taskId": task_id,
        "type": "validation",
        "round": int(resolved_round),
        "validatorId": str(validator_id),
        "path": str(report_path),
    }


def heartbeat(task_id: str, *, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Update lastActive for tracking records in the current round.

    Note: CLI invocations are separate processes, so heartbeats must not require
    PID affinity. We update any present tracking payloads for the task's current
    round and fail closed only when no tracking records exist at all.
    """
    ev = EvidenceService(task_id, project_root=project_root)
    round_num = int(ev.get_current_round() or 1)
    round_dir = ev.ensure_round(round_num)

    updated: List[str] = []
    now = utc_timestamp()

    # Implementation report (if present)
    impl = ev.read_implementation_report(round_num=round_num)
    if isinstance(impl, dict):
        tracking = impl.get("tracking")
        if isinstance(tracking, dict):
            tracking["lastActive"] = now
            impl["tracking"] = tracking
            ev.write_implementation_report(impl, round_num=round_num)
            updated.append(str(round_dir / ev.implementation_filename))

    # Validator reports in this round (if present)
    for p in ev.list_validator_reports(round_num=round_num):
        try:
            vid = _validator_id_from_path(p)
            data = ev.read_validator_report(vid, round_num=round_num)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        tr = data.get("tracking")
        if isinstance(tr, dict):
            tr["lastActive"] = now
            data["tracking"] = tr
            # p.stem is "validator-<id>-report" but EvidenceService accepts either.
            ev.write_validator_report(vid, data, round_num=round_num)
            updated.append(str(p))

    if not updated:
        raise RuntimeError("No tracking records found for this process")

    return {"taskId": task_id, "round": round_num, "updated": updated, "heartbeatAt": now}


def complete(
    task_id: str,
    *,
    project_root: Optional[Path] = None,
    implementation_status: str = "complete",
) -> Dict[str, Any]:
    """Mark tracking complete for the current process in the current round."""
    ev = EvidenceService(task_id, project_root=project_root)
    round_num = int(ev.get_current_round() or 1)
    round_dir = ev.ensure_round(round_num)

    updated: List[str] = []
    now = utc_timestamp()

    impl = ev.read_implementation_report(round_num=round_num)
    if isinstance(impl, dict):
        tr = impl.get("tracking")
        if isinstance(tr, dict) and int(tr.get("processId") or 0) == _pid():
            tr["lastActive"] = now
            tr["completedAt"] = now
            impl["tracking"] = tr
            # Track completion also stamps completionStatus by default.
            impl["completionStatus"] = str(implementation_status)
            ev.write_implementation_report(impl, round_num=round_num)
            updated.append(str(round_dir / ev.implementation_filename))

    for p in ev.list_validator_reports(round_num=round_num):
        vid = _validator_id_from_path(p)
        data = ev.read_validator_report(vid, round_num=round_num)
        if not isinstance(data, dict):
            continue
        tr = data.get("tracking")
        if isinstance(tr, dict) and int(tr.get("processId") or 0) == _pid():
            tr["lastActive"] = now
            tr["completedAt"] = now
            data["tracking"] = tr
            ev.write_validator_report(vid, data, round_num=round_num)
            updated.append(str(p))

    if not updated:
        raise RuntimeError("No tracking records found for this process")

    return {"taskId": task_id, "round": round_num, "updated": updated, "completedAt": now}


def list_active(*, project_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """List all active (in-progress) tracking records under the evidence tree."""
    from edison.core.qa._utils import get_evidence_base_path

    base = get_evidence_base_path(project_root)
    if not base.exists():
        return []

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
            out.append(
                {
                    "taskId": task_dir.name,
                    "type": "implementation",
                    "round": int(round_num),
                    "processId": tr.get("processId"),
                    "startedAt": tr.get("startedAt"),
                    "lastActive": tr.get("lastActive"),
                    "path": str(latest / ev.implementation_filename),
                }
            )

        # Validator reports
        for p in ev.list_validator_reports(round_num=round_num):
            vid = _validator_id_from_path(p)
            data = ev.read_validator_report(vid, round_num=round_num)
            if not isinstance(data, dict):
                continue
            if str(data.get("verdict") or "").strip().lower() != "pending":
                continue
            tr = data.get("tracking") if isinstance(data.get("tracking"), dict) else {}
            out.append(
                {
                    "taskId": task_dir.name,
                    "type": "validation",
                    "validatorId": data.get("validatorId"),
                    "round": int(round_num),
                    "processId": tr.get("processId"),
                    "startedAt": tr.get("startedAt"),
                    "lastActive": tr.get("lastActive"),
                    "path": str(p),
                }
            )

    return out


__all__ = [
    "start_implementation",
    "start_validation",
    "heartbeat",
    "complete",
    "list_active",
]
