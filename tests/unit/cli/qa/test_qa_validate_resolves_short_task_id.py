from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    full_task_id = "96-wave1-resolve-short-id"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_task_id, title="Test", create_qa=False)

    EvidenceService(full_task_id, project_root=isolated_project_env).ensure_round(1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id="96",
            scope=None,
            session=None,
            round=1,
            wave=None,
            preset=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=False,
            sequential=False,
            dry_run=True,
            max_workers=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["task_id"] == full_task_id
    assert payload["roster"]["taskId"] == full_task_id
