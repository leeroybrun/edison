from __future__ import annotations

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
        processId=12345,
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
        processId=12345,
        completedAt=now,
        lastActive=now,
    )

    active2 = list_processes(repo_root=repo, active_only=True)
    assert not any(p.get("runId") == run_id for p in active2)

    all_procs = list_processes(repo_root=repo, active_only=False)
    stopped = [p for p in all_procs if p.get("runId") == run_id]
    assert stopped and stopped[0].get("state") == "stopped"

