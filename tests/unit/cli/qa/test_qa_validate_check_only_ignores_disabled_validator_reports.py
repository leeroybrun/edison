from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_check_only_ignores_disabled_validator_reports(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    """A disabled validator must not become blocking just because a report exists.

    This is important when a validator was previously enabled, produced a report,
    and was later disabled for the repo. Validation should ignore it rather than
    fail-closed on stale artifacts.
    """
    monkeypatch.chdir(isolated_project_env)

    project_dir = isolated_project_env / ".edison" / "config"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "validation.yaml").write_text(
        "validation:\n"
        "  defaultPreset: quick\n"
        "  presets:\n"
        "    quick:\n"
        "      name: quick\n"
        "      validators: []\n"
        "      required_evidence: []\n"
        "      blocking_validators: []\n"
        "  validators:\n"
        "    global-codex:\n"
        "      enabled: false\n"
        "    global-claude:\n"
        "      enabled: false\n"
        "    global-gemini:\n"
        "      enabled: false\n",
        encoding="utf-8",
    )

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_repo = TaskRepository(project_root=isolated_project_env)

    task_id = "T-ROOT"
    task_repo.save(Task.create(task_id, "Root", state=wf.get_semantic_state("task", "done")))

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.update_metadata(round_num=1)

    # Create a stale blocking report for a disabled validator.
    ev.write_validator_report(
        "global-codex",
        {"taskId": task_id, "round": 1, "validatorId": "global-codex", "verdict": "reject"},
        round_num=1,
    )

    from edison.cli.qa.round.summarize_verdict import main as summarize_main

    rc = summarize_main(
        argparse.Namespace(
            task_id=task_id,
            scope="auto",
            session=None,
            round=1,
            preset="quick",
            add_validators=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("approved") is True
