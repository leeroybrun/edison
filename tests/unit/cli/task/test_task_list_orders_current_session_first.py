from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_list_orders_current_session_tasks_first(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow
    from edison.cli.task.list import main as list_main

    session_id = "sess-order-1"
    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id="T-GLOBAL", title="Global task", session_id=None, create_qa=False)
    workflow.create_task(task_id="T-SESS", title="Session task", session_id=None, create_qa=False)
    workflow.claim_task("T-SESS", session_id)

    # Make the session detectable without passing --session explicitly.
    monkeypatch.setenv("AGENTS_SESSION", session_id)

    rc = list_main(
        argparse.Namespace(
            status=None,
            session=None,
            type="task",
            all=False,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert out.find("T-SESS") < out.find("T-GLOBAL")

