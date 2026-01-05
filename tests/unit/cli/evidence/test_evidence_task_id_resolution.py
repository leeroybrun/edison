from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_evidence_init_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "011-task-relationships-mutators"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)

    from edison.cli.evidence.init import main as init_main

    rc = init_main(
        argparse.Namespace(
            task_id="011",
            round=1,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id
    expected_round = isolated_project_env / ".project" / "qa" / "validation-evidence" / full_id / "round-1"
    assert expected_round.exists()


@pytest.mark.qa
def test_evidence_status_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Require only a single evidence file so status can pass.
    cfg = isolated_project_env / ".edison" / "config" / "validation.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "012-task-relationships-consumers"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    ev = EvidenceService(task_id=full_id, project_root=isolated_project_env)
    round_dir = ev.ensure_round(1)

    fp = compute_repo_fingerprint(isolated_project_env)
    write_command_evidence(
        path=round_dir / "command-test.txt",
        task_id=full_id,
        round_num=1,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output="ok\n",
        fingerprint=fp,
    )

    from edison.cli.evidence.status import main as status_main

    rc = status_main(
        argparse.Namespace(
            task_id="012",
            round_num=1,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id


@pytest.mark.qa
def test_evidence_show_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Require only a single evidence file so show can parse expected content.
    cfg = isolated_project_env / ".edison" / "config" / "validation.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "089-context7-task-scoped-detection"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    ev = EvidenceService(task_id=full_id, project_root=isolated_project_env)
    round_dir = ev.ensure_round(1)

    fp = compute_repo_fingerprint(isolated_project_env)
    write_command_evidence(
        path=round_dir / "command-test.txt",
        task_id=full_id,
        round_num=1,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output="ok\n",
        fingerprint=fp,
    )

    from edison.cli.evidence.show import main as show_main

    rc = show_main(
        argparse.Namespace(
            task_id="089",
            round_num=1,
            filename="command-test.txt",
            command_name=None,
            raw=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id


@pytest.mark.qa
def test_evidence_context7_list_resolves_short_task_id(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.workflow import TaskQAWorkflow

    full_id = "090-context7-other"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=full_id, title="Test", create_qa=False)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.text.frontmatter import format_frontmatter

    ev = EvidenceService(task_id=full_id, project_root=isolated_project_env)
    round_dir = ev.ensure_round(1)

    marker = round_dir / "context7-react.txt"
    marker.write_text(
        format_frontmatter(
            {
                "package": "react",
                "libraryId": "/facebook/react",
                "topics": ["hooks"],
                "queriedAt": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    from edison.cli.evidence.context7 import main as context7_main

    rc = context7_main(
        argparse.Namespace(
            subcommand="list",
            task_id="090",
            round_num=1,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("taskId") == full_id
    markers = payload.get("markers") or []
    assert any(m.get("package") == "react" for m in markers)
