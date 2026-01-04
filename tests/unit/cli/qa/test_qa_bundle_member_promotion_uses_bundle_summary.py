from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_promote_bundle_member_done_to_validated_uses_root_bundle_summary(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_done = wf.get_semantic_state("task", "done")
    task_validated = wf.get_semantic_state("task", "validated")
    qa_done = wf.get_semantic_state("qa", "done")
    qa_validated = wf.get_semantic_state("qa", "validated")

    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.task import TaskRepository
    from edison.core.task.models import Task

    task_repo = TaskRepository(project_root=isolated_project_env)
    qa_repo = QARepository(project_root=isolated_project_env)

    root_task_id = "210-bundle-root"
    member_task_id = "211-bundle-member"

    task_repo.create(Task(id=root_task_id, state=task_done, title="Root"))
    task_repo.create(Task(id=member_task_id, state=task_done, title="Member"))

    qa_repo.create(QARecord(id=f"{root_task_id}-qa", task_id=root_task_id, state=qa_done, title="QA root"))
    qa_repo.create(QARecord(id=f"{member_task_id}-qa", task_id=member_task_id, state=qa_done, title="QA member"))

    # Evidence: root has validator reports; member only has a mirrored bundle summary.
    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorRegistry

    root_ev = EvidenceService(root_task_id, project_root=isolated_project_env)
    member_ev = EvidenceService(member_task_id, project_root=isolated_project_env)

    root_ev.ensure_round(1)
    member_ev.ensure_round(1)

    # Task done→validated guard requires an implementation report for the current round.
    root_ev.write_implementation_report(
        {"taskId": root_task_id, "round": 1, "completionStatus": "complete"},
        round_num=1,
    )
    member_ev.write_implementation_report(
        {"taskId": member_task_id, "round": 1, "completionStatus": "complete"},
        round_num=1,
    )

    registry = ValidatorRegistry(project_root=isolated_project_env)
    roster = registry.build_execution_roster(task_id=root_task_id, session_id=None)
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

    for vid in sorted(set(blocking_ids)):
        root_ev.write_validator_report(
            vid,
            {"taskId": root_task_id, "round": 1, "validatorId": vid, "verdict": "approve"},
            round_num=1,
        )

    bundle_summary = {
        "taskId": root_task_id,
        "rootTask": root_task_id,
        "scope": "bundle",
        "round": 1,
        "approved": True,
        "tasks": [{"taskId": root_task_id}, {"taskId": member_task_id}],
        "validators": [{"validatorId": vid, "verdict": "approve"} for vid in sorted(set(blocking_ids))],
        "missing": [],
    }
    root_ev.write_bundle(bundle_summary, round_num=1)
    # Mirror into member evidence dir so per-task checks can resolve.
    member_ev.write_bundle({**bundle_summary, "taskId": member_task_id}, round_num=1)

    from edison.cli.qa.promote import main as promote_main
    from edison.cli.qa.promote import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([member_task_id, "--status", qa_validated, "--repo-root", str(isolated_project_env)])

    rc = promote_main(args)
    assert rc == 0

    # Member task and QA should be validated.
    member_after = task_repo.get(member_task_id)
    assert member_after is not None
    assert member_after.state == task_validated

    qa_after = qa_repo.get(f"{member_task_id}-qa")
    assert qa_after is not None
    assert qa_after.state == qa_validated

