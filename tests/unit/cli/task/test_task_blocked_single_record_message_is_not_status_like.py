from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_blocked_single_record_text_is_not_status_like(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-blocked-1"
    task_id = "300.1.1.2-wave2-fix-leak-check-test"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    from edison.cli.task.blocked import main as blocked_main

    rc = blocked_main(
        argparse.Namespace(
            record_id="300.1.1.2",
            session=None,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "NOT BLOCKED" in out or "BLOCKED" in out
    assert "READY" not in out
    assert "state=" in out

