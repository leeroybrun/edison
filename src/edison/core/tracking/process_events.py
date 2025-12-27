from __future__ import annotations

import json
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from edison.core.audit.jsonl import append_jsonl
from edison.core.utils.config import load_validated_section
from edison.core.utils.time import parse_iso8601, utc_now, utc_timestamp


def _pid_is_running(*, process_id: Any, hostname: Any) -> bool | None:
    """Best-effort liveness check for a PID on the current host.

    Returns:
        - True/False when liveness can be determined locally
        - None when liveness cannot be determined (e.g., remote host)
    """
    try:
        pid = int(process_id)
    except Exception:
        return None

    host = str(hostname or "").strip()
    if host and host != socket.gethostname():
        return None

    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None
    return True


def _active_stale_seconds(*, repo_root: Path | None) -> int:
    cfg = load_validated_section(
        ["orchestration", "tracking"],
        required_fields=["activeStaleSeconds"],
        repo_root=repo_root,
    )
    return int(cfg["activeStaleSeconds"])


def _is_stale(*, repo_root: Path | None, last_active: Any) -> bool | None:
    try:
        ts = str(last_active or "").strip()
        if not ts:
            return None
        last_dt = parse_iso8601(ts, repo_root=repo_root)
        now_dt = utc_now(repo_root=repo_root)
        age_seconds = (now_dt - last_dt).total_seconds()
        return age_seconds > float(_active_stale_seconds(repo_root=repo_root))
    except Exception:
        return None


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


def list_processes(
    *,
    repo_root: Path | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Compute a process index from the append-only JSONL process event stream."""
    path = _process_events_path(repo_root=repo_root)
    if path is None or not path.exists():
        return []

    latest_by_run: dict[str, dict[str, Any]] = {}
    for ev in _iter_jsonl(path):
        rid = str(ev.get("runId") or "").strip()
        if not rid:
            continue
        latest_by_run[rid] = ev

    out: list[dict[str, Any]] = []
    for rid, ev in latest_by_run.items():
        last_event = str(ev.get("event") or "").strip()
        state = "stopped" if last_event.endswith(".completed") else "active"
        if active_only and state != "active":
            continue

        item: dict[str, Any] = {
            "runId": rid,
            "state": state,
            "event": last_event,
            "ts": ev.get("ts"),
            "kind": ev.get("kind"),
            "taskId": ev.get("taskId"),
            "round": ev.get("round"),
            "validatorId": ev.get("validatorId"),
            "sessionId": ev.get("sessionId"),
            "model": ev.get("model"),
            "processId": ev.get("processId"),
            "hostname": ev.get("hostname"),
            "startedAt": ev.get("startedAt"),
            "lastActive": ev.get("lastActive"),
            "completedAt": ev.get("completedAt"),
        }

        item["isRunning"] = _pid_is_running(process_id=item.get("processId"), hostname=item.get("hostname"))
        item["isStale"] = _is_stale(repo_root=repo_root, last_active=item.get("lastActive"))
        out.append(item)

    out.sort(key=lambda r: str(r.get("ts") or ""))
    return out


__all__ = [
    "append_process_event",
    "list_processes",
]

