from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_check_only_bundle_scope_writes_root_summary_and_mirrors(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.repository import TaskRepository

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_repo = TaskRepository(project_root=isolated_project_env)

    root_task_id = "T-ROOT"
    member_task_id = "T-MEMBER"

    task_repo.save(Task.create(root_task_id, "Root", state=wf.get_semantic_state("task", "done")))
    task_repo.save(Task.create(member_task_id, "Member", state=wf.get_semantic_state("task", "done")))

    rel = TaskRelationshipService(project_root=isolated_project_env)
    rel.add(task_id=member_task_id, rel_type="bundle_root", target_id=root_task_id, force=True)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.registries.validators import ValidatorRegistry

    root_ev = EvidenceService(root_task_id, project_root=isolated_project_env)
    root_ev.ensure_round(1)
    root_ev.update_metadata(round_num=1)

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

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=member_task_id,
            scope="bundle",
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
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("approved") is True

    # Root summary exists and includes scope + rootTask.
    root_bundle = root_ev.read_bundle(round_num=1)
    assert root_bundle is not None
    assert root_bundle.get("rootTask") == root_task_id
    assert root_bundle.get("scope") == "bundle"
    task_ids = {t.get("taskId") for t in (root_bundle.get("tasks") or [])}
    assert task_ids == {root_task_id, member_task_id}

    # Member bundle summary IS mirrored so session close/verify can enforce per-task
    # bundle approval even when validation runs once at the bundle root.
    member_ev = EvidenceService(member_task_id, project_root=isolated_project_env)
    member_bundle = member_ev.read_bundle(round_num=1)
    assert member_bundle is not None
    assert member_bundle.get("taskId") == member_task_id
    assert member_bundle.get("rootTask") == root_task_id
    assert member_bundle.get("scope") == "bundle"
    mirrored_task_ids = {t.get("taskId") for t in (member_bundle.get("tasks") or [])}
    assert mirrored_task_ids == {root_task_id, member_task_id}
