from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_status_prints_session_banner_when_session_scoped(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-status-banner-1"
    task_id = "12011-wave8-legacy"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    from edison.cli.task.status import main as status_main

    rc = status_main(
        argparse.Namespace(
            record_id="12011",
            status=None,
            reason=None,
            type=None,
            dry_run=False,
            force=False,
            session=None,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    captured = capsys.readouterr()
    assert "session-scoped" in captured.err
    assert session_id in captured.err
    assert ".project/sessions/" in captured.err
    assert "Status:" in captured.out

