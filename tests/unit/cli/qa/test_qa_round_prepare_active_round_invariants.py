from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_round_prepare_reuses_latest_round_when_not_finalized(
    isolated_project_env: Path, monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.cli.qa.round.prepare import main as prepare_main
    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "910-wave1-active-round"
    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Task", create_qa=True)

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
    assert ev.get_current_round() == 1

    # Not finalized: prepare must reuse the same open round, not allocate a new one.
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
    assert ev.get_current_round() == 1


@pytest.mark.qa
def test_qa_round_prepare_creates_next_round_when_latest_is_finalized(
    isolated_project_env: Path, monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.cli.qa.round.prepare import main as prepare_main
    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "911-wave1-finalized-round"
    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Task", create_qa=True)

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
    assert ev.get_current_round() == 1

    # Mark round-1 as finalized.
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
    assert ev.get_current_round() == 2

