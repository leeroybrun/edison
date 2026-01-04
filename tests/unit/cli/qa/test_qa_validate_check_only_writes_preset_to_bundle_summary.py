from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_check_only_writes_preset_to_bundle_summary(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "920-wave1-check-only-preset"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            preset="strict",
            session=None,
            round=1,
            new_round=False,
            wave=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=False,
            check_only=True,
            sequential=False,
            dry_run=False,
            max_workers=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc in (0, 1)

    data = ev.read_bundle(round_num=1)
    assert data.get("preset") == "strict"

