from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


def test_process_events_index_tracks_active_and_completed(isolated_project_env: Path) -> None:
    from edison.core.tracking.process_events import append_process_event, list_processes
    from edison.core.utils.time import utc_timestamp

    repo = isolated_project_env
    now = utc_timestamp(repo_root=repo)

    run_id = append_process_event(
        "process.started",
        repo_root=repo,
        kind="implementation",
        taskId="T-PROC-1",
        round=1,
        model="codex",
        processId=os.getpid(),
        startedAt=now,
        lastActive=now,
    )
    assert run_id

    active = list_processes(repo_root=repo, active_only=True)
    assert any(p.get("runId") == run_id and p.get("state") == "active" for p in active)

    append_process_event(
        "process.completed",
        repo_root=repo,
        run_id=run_id,
        kind="implementation",
        taskId="T-PROC-1",
        round=1,
        model="codex",
        processId=os.getpid(),
        completedAt=now,
        lastActive=now,
    )

    active2 = list_processes(repo_root=repo, active_only=True)
    assert not any(p.get("runId") == run_id for p in active2)

    all_procs = list_processes(repo_root=repo, active_only=False)
    stopped = [p for p in all_procs if p.get("runId") == run_id]
    assert stopped and stopped[0].get("state") == "stopped"


def test_list_processes_records_stop_event_when_pid_is_dead(isolated_project_env: Path) -> None:
    from edison.core.tracking.process_events import append_process_event, list_processes
    from edison.core.utils.time import utc_timestamp

    repo = isolated_project_env
    now = utc_timestamp(repo_root=repo)

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.05)"])
    proc.wait(timeout=5)

    run_id = append_process_event(
        "process.started",
        repo_root=repo,
        kind="orchestrator",
        sessionId="sess-dead",
        model="codex",
        processId=proc.pid,
        startedAt=now,
        lastActive=now,
    )
    assert run_id

    active = list_processes(repo_root=repo, active_only=True)
    assert not any(p.get("runId") == run_id for p in active)

    all_procs = list_processes(repo_root=repo, active_only=False)
    matching = [p for p in all_procs if p.get("runId") == run_id]
    assert matching and matching[0].get("state") == "stopped"
    assert str(matching[0].get("event") or "") == "process.detected_stopped"

    jsonl = repo / ".project" / "logs" / "edison" / "process-events.jsonl"
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert any((f"\"runId\": \"{run_id}\"" in ln and "\"event\": \"process.detected_stopped\"" in ln) for ln in lines)
