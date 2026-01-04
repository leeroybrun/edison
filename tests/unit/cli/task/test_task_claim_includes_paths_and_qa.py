from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_claim_json_includes_paths_and_auto_qa(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.workflow.repository import QARepository
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-claim-1"
    task_id = "12007-wave8-db-remove-tracked-prisma-backups"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)

    assert QARepository(project_root=isolated_project_env).get(f"{task_id}-qa") is None

    from edison.cli.task.claim import main as claim_main

    rc = claim_main(
        argparse.Namespace(
            record_id="12007",
            session=session_id,
            type=None,
            owner=None,
            status=None,
            takeover=False,
            reclaim=False,
            reason=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["record_id"] == task_id
    assert payload["session_id"] == session_id
    assert payload["path"].startswith(".project/")
    assert payload["evidenceRoot"].startswith(".project/")
    assert payload["qaId"] == f"{task_id}-qa"
    assert payload["qaCreated"] is True
    assert payload["qaPath"].startswith(".project/")
    assert isinstance(payload["nextSteps"], list) and payload["nextSteps"]

    assert QARepository(project_root=isolated_project_env).get(f"{task_id}-qa") is not None
