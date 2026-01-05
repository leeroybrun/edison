from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_list_includes_session_for_session_scoped_records(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-list-1"
    task_id = "300.2.1.1-wave2-foo"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    from edison.cli.task.list import main as list_main

    rc = list_main(
        argparse.Namespace(
            status="wip",
            session=None,
            type="task",
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert task_id in out
    assert f"session={session_id}" in out

