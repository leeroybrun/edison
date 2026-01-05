from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest


@pytest.mark.qa
def test_evidence_capture_failure_prints_actionable_env_hint(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    py = sys.executable.replace("\\", "\\\\")
    (isolated_project_env / ".edison" / "config" / "ci.yaml").write_text(
        f"ci:\n  commands:\n    test: \"{py} -c \\\"raise SystemExit(2)\\\"\"\n",
        encoding="utf-8",
    )
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "220-wave1-evidence-capture-failure-hint"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)
    EvidenceService(task_id=task_id, project_root=isolated_project_env).ensure_round(1)

    from edison.cli.evidence.capture import main as capture_main

    rc = capture_main(
        argparse.Namespace(
            task_id=task_id,
            only=["test"],
            all=False,
            preset=None,
            session_close=False,
            command_name=None,
            continue_on_failure=False,
            round_num=1,
            no_lock=False,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 1

    captured = capsys.readouterr()
    assert "Evidence:" in captured.err
    assert f".project/qa/validation-evidence/{task_id}/round-1/command-test.txt" in captured.err
    assert ".edison/config/ci.yaml" in captured.err
    assert "ci.commands.test" in captured.err

