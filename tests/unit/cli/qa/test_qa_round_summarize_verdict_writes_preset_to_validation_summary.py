from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_round_summarize_verdict_writes_preset_to_validation_summary(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "920-wave1-round-summarize-preset"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)

    from edison.cli.qa.round.summarize_verdict import main as summarize_main

    rc = summarize_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            preset="strict",
            session=None,
            round=1,
            add_validators=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc in (0, 1)

    data = ev.read_bundle(round_num=1)
    assert data.get("preset") == "strict"
