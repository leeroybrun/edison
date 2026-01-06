from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_dry_run_json_includes_preflight_checklist(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "150-wave1-preflight"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=task_id,
            session=None,
            round=None,
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
    assert payload["checklist"]["kind"] == "qa_validate_preflight"
    items = payload["checklist"]["items"]
    assert any(i.get("id") == "evidence-round" for i in items)
    assert any(i.get("id") == "engine-availability" for i in items)
    assert any(i.get("id") == "scope-preset" for i in items)


@pytest.mark.qa
def test_qa_validate_dry_run_text_shows_evidence_round_dir(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "151-wave1-preflight-text"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=task_id,
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
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    expected = str(Path(".project/qa/validation-reports") / task_id / "round-1")
    assert expected in out
