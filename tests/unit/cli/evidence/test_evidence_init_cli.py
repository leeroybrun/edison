from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def test_evidence_init_is_deprecated_and_does_not_create_rounds(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_id = "task-evidence-init-001"

    from edison.core.task.workflow import TaskQAWorkflow

    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    from edison.cli.evidence.init import main as init_main

    args = argparse.Namespace(
        task_id=task_id,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = init_main(args)
    assert rc == 1

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("deprecated") is True
    assert payload.get("taskId") == task_id

    evidence_root = isolated_project_env / ".project" / "qa" / "validation-reports" / task_id
    assert not evidence_root.exists()
