from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_show_prints_session_banner_when_session_scoped(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-show-1"
    task_id = "12009-wave8-legacy"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    from edison.cli.task.show import main as show_main

    rc = show_main(
        argparse.Namespace(
            task_id="12009",
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    captured = capsys.readouterr()
    assert "session-scoped" in captured.err
    assert session_id in captured.err
    assert ".project/sessions/" in captured.err
    # Raw markdown still printed to stdout
    assert "id:" in captured.out


@pytest.mark.task
def test_task_show_does_not_print_session_banner_when_running_in_that_session(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-show-2"
    task_id = "12010-wave8-legacy"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    monkeypatch.setenv("AGENTS_SESSION", session_id)

    from edison.cli.task.show import main as show_main

    rc = show_main(
        argparse.Namespace(
            task_id="12010",
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    captured = capsys.readouterr()
    assert captured.err.strip() == ""
    assert "id:" in captured.out
