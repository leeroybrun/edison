from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_round_prepare_copies_forward_implementation_report(
    isolated_project_env: Path, monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.cli.qa.round.prepare import main as prepare_main
    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "920-wave1-copy-forward"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Task", create_qa=True)

    # Prepare round 1 (creates report)
    rc1 = prepare_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            session=None,
            status="pending",
            note=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc1 == 0

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    r1 = ev.get_round_dir(1)
    report1 = r1 / "implementation-report.md"
    assert report1.exists()

    # Add some content to round 1 body so we can verify it is copied.
    ev.write_implementation_report(
        {"taskId": task_id, "round": 1},
        round_num=1,
        body="\n# Implementation Report\n\nOriginal content\n",
        preserve_existing_body=False,
    )

    # Finalize round 1 so prepare allocates round 2.
    ev.write_bundle(
        {
            "taskId": task_id,
            "rootTask": task_id,
            "scope": "hierarchy",
            "round": 1,
            "approved": False,
            "status": "final",
        },
        round_num=1,
    )

    rc2 = prepare_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            session=None,
            status="pending",
            note=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc2 == 0

    r2 = ev.get_round_dir(2)
    report2 = r2 / "implementation-report.md"
    assert report2.exists()
    body2 = report2.read_text(encoding="utf-8", errors="ignore")

    assert "Original content" in body2
    assert "## Changes in this round (required)" in body2

