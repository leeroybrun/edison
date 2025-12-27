from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable

from edison.core.audit.jsonl import append_jsonl
from edison.core.tracking.liveness import is_stale, pid_is_running
from edison.core.utils.config import load_validated_section
from edison.core.utils.time import utc_timestamp


def _process_events_path(*, repo_root: Path | None) -> Path | None:
    try:
        cfg = load_validated_section(
            ["orchestration", "tracking"],
            required_fields=["processEventsJsonl"],
            repo_root=repo_root,
        )
        raw = str(cfg.get("processEventsJsonl") or "").strip()
        if not raw:
            return None
        p = Path(raw).expanduser()
        if not p.is_absolute():
            from edison.core.utils.paths import PathResolver

            root = repo_root or PathResolver.resolve_project_root()
            p = (Path(root) / p).resolve()
        return p
    except Exception:
        return None


def _is_stop_event(event: str) -> bool:
    ev = str(event or "").strip().lower()
    return ev.endswith(".completed") or ev.endswith(".stopped")


def _non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def append_process_event(
    event: str,
    *,
    repo_root: Path | None = None,
    run_id: str | None = None,
    **fields: Any,
) -> str | None:
    """Append a single process event to the configured JSONL stream (fail-open).

    Returns the run id used for the event (generated when omitted), or None when
    event logging is unavailable.
    """
    path = _process_events_path(repo_root=repo_root)
    if path is None:
        return None

    rid = str(run_id).strip() if run_id else ""
    if not rid:
        rid = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "ts": utc_timestamp(repo_root=repo_root),
        "event": str(event),
        "runId": rid,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
    }
    payload.update(fields)

    try:
        append_jsonl(path=path, payload=payload, repo_root=repo_root)
    except Exception:
        return None

    return rid


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except FileNotFoundError:
        return
    except Exception:
        return


_INDEX_FIELDS = {
    "kind",
    "taskId",
    "round",
    "validatorId",
    "sessionId",
    "model",
    "processId",
    "hostname",
    "processHostname",
    "startedAt",
    "lastActive",
    "completedAt",
    "stoppedAt",
    "stopReason",
    "continuationId",
    "launcherKind",
    "launcherPid",
    "parentPid",
    "agentRole",
    "zenRole",
}


def _compute_index(
    *,
    repo_root: Path | None,
    update_stop_events: bool,
) -> tuple[list[dict[str, Any]], int]:
    path = _process_events_path(repo_root=repo_root)
    if path is None or not path.exists():
        return ([], 0)

    runs: dict[str, dict[str, Any]] = {}
    for ev in _iter_jsonl(path):
        rid = str(ev.get("runId") or "").strip()
        if not rid:
            continue
        state = runs.setdefault(
            rid,
            {
                "runId": rid,
                "lastEvent": "",
                "ts": "",
                "fields": {},
            },
        )
        state["lastEvent"] = str(ev.get("event") or "").strip()
        state["ts"] = ev.get("ts") or state.get("ts")
        fields = state.get("fields") if isinstance(state.get("fields"), dict) else {}
        for k, v in ev.items():
            if k in {"ts", "event", "runId"}:
                continue
            if k not in _INDEX_FIELDS:
                continue
            if _non_empty(v):
                fields[k] = v
        state["fields"] = fields
        runs[rid] = state

    stop_events_to_append: list[dict[str, Any]] = []
    out: list[dict[str, Any]] = []

    for rid, state in runs.items():
        last_event = str(state.get("lastEvent") or "").strip()
        fields = state.get("fields") if isinstance(state.get("fields"), dict) else {}

        process_host = fields.get("processHostname") or fields.get("hostname") or socket.gethostname()
        item: dict[str, Any] = {
            "runId": rid,
            "event": last_event,
            "ts": state.get("ts"),
            "state": "stopped" if _is_stop_event(last_event) else "active",
            **{k: fields.get(k) for k in _INDEX_FIELDS if k in fields},
        }

        # Avoid re-checking liveness for historical/stopped runs.
        if item.get("state") == "stopped":
            item["isRunning"] = False
            item["isStale"] = None
        else:
            item["isRunning"] = pid_is_running(process_id=item.get("processId"), hostname=process_host)
            item["isStale"] = is_stale(repo_root=repo_root, last_active=item.get("lastActive"))

        if update_stop_events and item.get("state") == "active" and item.get("isRunning") is False:
            stopped_at = utc_timestamp(repo_root=repo_root)
            stop_ev = {
                "event": "process.detected_stopped",
                "runId": rid,
                "kind": item.get("kind"),
                "taskId": item.get("taskId"),
                "round": item.get("round"),
                "validatorId": item.get("validatorId"),
                "sessionId": item.get("sessionId"),
                "model": item.get("model"),
                "processId": item.get("processId"),
                "hostname": item.get("hostname") or socket.gethostname(),
                "processHostname": item.get("processHostname") or process_host,
                "startedAt": item.get("startedAt"),
                "lastActive": item.get("lastActive"),
                "stoppedAt": stopped_at,
                "stopReason": "pid_not_running",
            }
            stop_events_to_append.append(stop_ev)

            item["event"] = "process.detected_stopped"
            item["ts"] = stopped_at
            item["state"] = "stopped"
            item["stoppedAt"] = stopped_at
            item["stopReason"] = "pid_not_running"
            item["isRunning"] = False
            item["isStale"] = None

        out.append(item)

    recorded = 0
    if update_stop_events and stop_events_to_append:
        for stop_ev in stop_events_to_append:
            append_process_event(
                str(stop_ev["event"]),
                repo_root=repo_root,
                run_id=str(stop_ev["runId"]),
                kind=stop_ev.get("kind"),
                taskId=stop_ev.get("taskId"),
                round=stop_ev.get("round"),
                validatorId=stop_ev.get("validatorId"),
                sessionId=stop_ev.get("sessionId"),
                model=stop_ev.get("model"),
                processId=stop_ev.get("processId"),
                hostname=stop_ev.get("hostname"),
                processHostname=stop_ev.get("processHostname"),
                startedAt=stop_ev.get("startedAt"),
                lastActive=stop_ev.get("lastActive"),
                stoppedAt=stop_ev.get("stoppedAt"),
                stopReason=stop_ev.get("stopReason"),
            )
            recorded += 1

    out.sort(key=lambda r: str(r.get("ts") or ""))
    return (out, recorded)


def list_processes(
    *,
    repo_root: Path | None = None,
    active_only: bool = True,
    update_stop_events: bool = True,
) -> list[dict[str, Any]]:
    """Compute a process index from the append-only JSONL process event stream."""
    out, _ = _compute_index(repo_root=repo_root, update_stop_events=update_stop_events)
    if not active_only:
        return out
    return [p for p in out if p.get("state") == "active"]


def sweep_processes(*, repo_root: Path | None = None) -> dict[str, Any]:
    procs, recorded = _compute_index(repo_root=repo_root, update_stop_events=True)
    checked = len([p for p in procs if p.get("state") == "active"])
    return {"stoppedRecorded": int(recorded), "checkedActive": int(checked)}


__all__ = [
    "append_process_event",
    "list_processes",
    "sweep_processes",
]
