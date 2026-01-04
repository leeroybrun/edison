from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_preflight_bundle_scope_uses_root_evidence_round(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.workflow import TaskQAWorkflow

    root_task = "910-wave1-bundle-root"
    member_task = "911-wave1-bundle-member"
    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=root_task, title="Root", create_qa=False)
    workflow.create_task(task_id=member_task, title="Member", create_qa=False)

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id=member_task,
        rel_type="bundle_root",
        target_id=root_task,
    )

    root_ev = EvidenceService(root_task, project_root=isolated_project_env)
    root_ev.ensure_round(1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=member_task,
            scope="bundle",
            session=None,
            round=1,
            new_round=False,
            wave=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=False,
            check_only=False,
            sequential=False,
            dry_run=True,
            max_workers=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    checklist = payload["checklist"]

    evidence_item = next(i for i in checklist["items"] if i["id"] == "evidence-round")
    expected = str(Path(".project/qa/validation-evidence") / root_task / "round-1")
    assert expected in (evidence_item.get("evidencePaths") or [])

