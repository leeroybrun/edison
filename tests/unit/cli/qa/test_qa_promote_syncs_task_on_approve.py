from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_qa_promote_done_to_validated_syncs_task_done_to_validated(
    isolated_project_env: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(isolated_project_env)

    task_id = "200-qa-promote-sync"
    qa_id = f"{task_id}-qa"

    from edison.core.config.domains.workflow import WorkflowConfig

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_done = wf.get_semantic_state("task", "done")
    task_validated = wf.get_semantic_state("task", "validated")
    qa_done = wf.get_semantic_state("qa", "done")
    qa_validated = wf.get_semantic_state("qa", "validated")

    # Create task + QA directly in their respective "done" directories.
    from edison.core.task import TaskRepository
    from edison.core.task.models import Task

    task_repo = TaskRepository(project_root=isolated_project_env)
    task_repo.create(Task(id=task_id, state=task_done, title="Task"))

    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository

    qa_repo = QARepository(project_root=isolated_project_env)
    qa_repo.create(QARecord(id=qa_id, task_id=task_id, state=qa_done, title="QA"))

    # Create evidence so QA done→validated is allowed (bundle approved + blocking validator reports).
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorRegistry

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.update_metadata(round_num=1)

    # Task done→validated guard requires an implementation report for the current round.
    ev.write_implementation_report(
        {
            "taskId": task_id,
            "round": 1,
            "completionStatus": "complete",
        },
        round_num=1,
    )

    registry = ValidatorRegistry(project_root=isolated_project_env)
    roster = registry.build_execution_roster(task_id=task_id, session_id=None)
    candidates = (
        roster.get("alwaysRequired", [])
        + roster.get("triggeredBlocking", [])
        + roster.get("triggeredOptional", [])
    )
    blocking_ids = [
        str(v.get("id"))
        for v in candidates
        if isinstance(v, dict) and v.get("blocking") and v.get("id")
    ]
    assert blocking_ids, "test setup expects at least one blocking validator"

    # Write validator reports first, then bundle summary, so the bundle isn't considered stale.
    for vid in sorted(set(blocking_ids)):
        ev.write_validator_report(
            vid,
            {
                "taskId": task_id,
                "round": 1,
                "validatorId": vid,
                "verdict": "approve",
            },
            round_num=1,
        )

    ev.write_bundle(
        {
            "taskId": task_id,
            "round": 1,
            "approved": True,
        },
        round_num=1,
    )

    # Promote QA: done -> validated, and expect task sync (done -> validated).
    from edison.cli.qa.promote import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        [task_id, "--status", qa_validated, "--repo-root", str(isolated_project_env)]
    )

    rc = main(args)
    assert rc == 0

    # Verify task moved to validated state.
    task_after = task_repo.get(task_id)
    assert task_after is not None
    assert task_after.state == task_validated

    # Sanity: QA is validated too.
    qa_after = qa_repo.get(qa_id)
    assert qa_after is not None
    assert qa_after.state == qa_validated

    out = capsys.readouterr().out
    assert f"Promoted {qa_id}: {qa_done} -> {qa_validated}" in out
