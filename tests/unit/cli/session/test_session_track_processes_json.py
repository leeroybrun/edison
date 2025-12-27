from __future__ import annotations

import argparse
import json
from pathlib import Path


def test_session_track_processes_outputs_json(isolated_project_env: Path, capsys) -> None:
    from edison.cli.session import track as track_cmd
    from edison.core.tracking.process_events import append_process_event
    from edison.core.utils.time import utc_timestamp

    repo = isolated_project_env
    now = utc_timestamp(repo_root=repo)

    run_id = append_process_event(
        "process.started",
        repo_root=repo,
        kind="orchestrator",
        sessionId="sess-proc",
        model="codex",
        processId=12345,
        startedAt=now,
        lastActive=now,
    )
    assert run_id

    parser = argparse.ArgumentParser()
    track_cmd.register_args(parser)
    args = parser.parse_args(["processes", "--json", "--repo-root", str(repo)])
    rc = track_cmd.main(args)
    assert rc == 0

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["count"] >= 1
    assert any(p.get("runId") == run_id for p in payload["processes"])

