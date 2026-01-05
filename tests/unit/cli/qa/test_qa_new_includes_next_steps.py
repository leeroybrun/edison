from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_qa_new_resolves_short_task_id_and_emits_next_steps(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.workflow.repository import QARepository
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "12010-wave8-ctx"
    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)

    assert QARepository(project_root=isolated_project_env).get(f"{task_id}-qa") is None

    from edison.cli.qa.new import main as qa_new_main

    rc = qa_new_main(
        argparse.Namespace(
            task_id="12010",
            owner="_unassigned_",
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["task_id"] == task_id
    assert payload["qaId"] == f"{task_id}-qa"
    assert payload["qaCreated"] is True
    assert payload["qaPath"].startswith(".project/")
    assert isinstance(payload["nextSteps"], list) and payload["nextSteps"]

