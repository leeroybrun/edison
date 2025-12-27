from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def test_session_track_sweep_outputs_json(isolated_project_env: Path, capsys) -> None:
    from edison.cli.session import track as track_cmd
    from edison.core.tracking.process_events import append_process_event
    from edison.core.utils.time import utc_timestamp

    repo = isolated_project_env
    now = utc_timestamp(repo_root=repo)

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.05)"])
    proc.wait(timeout=5)

    run_id = append_process_event(
        "process.started",
        repo_root=repo,
        kind="orchestrator",
        sessionId="sess-sweep",
        model="codex",
        processId=proc.pid,
        startedAt=now,
        lastActive=now,
    )
    assert run_id

    parser = argparse.ArgumentParser()
    track_cmd.register_args(parser)
    args = parser.parse_args(["sweep", "--json", "--repo-root", str(repo)])
    rc = track_cmd.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out.strip() or "{}")
    assert payload.get("stoppedRecorded", 0) >= 1
