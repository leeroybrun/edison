from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_status_json_includes_path_and_evidence_root(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-status-1"
    task_id = "12008-wave8-api-tests"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    from edison.cli.task.status import main as status_main

    rc = status_main(
        argparse.Namespace(
            record_id="12008",
            status=None,
            reason=None,
            type=None,
            dry_run=False,
            force=False,
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["record_id"] == task_id
    assert payload["path"].startswith(".project/")
    assert payload["evidenceRoot"].startswith(".project/")

