from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_session_track_start_resolves_short_task_id(
    isolated_project_env: Path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "211-wave1-track-resolve-task-id"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)

    from edison.cli.session.track import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        [
            "start",
            "--task",
            "211",
            "--type",
            "implementation",
            "--round",
            "1",
            "--json",
            "--repo-root",
            str(isolated_project_env),
        ]
    )

    rc = main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id
    assert f"validation-reports/{full_id}/round-1/implementation-report.md" in str(payload.get("path") or "")

