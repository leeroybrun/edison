from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest


@pytest.mark.qa
def test_evidence_capture_reuses_complete_snapshot_by_default(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Minimal CI config for evidence capture (would fail if executed).
    py = sys.executable.replace("\\", "\\\\")
    (isolated_project_env / ".edison" / "config" / "ci.yaml").write_text(
        f"ci:\n  commands:\n    test: \"{py} -c \\\"raise SystemExit(2)\\\"\"\n",
        encoding="utf-8",
    )
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir
    from edison.core.task.workflow import TaskQAWorkflow
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    task_id = "240-wave1-evidence-capture-reuse"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    fp = compute_repo_fingerprint(isolated_project_env)
    key = current_snapshot_key(project_root=isolated_project_env)
    snap_dir = snapshot_dir(project_root=isolated_project_env, key=key)
    snap_dir.mkdir(parents=True, exist_ok=True)

    write_command_evidence(
        path=snap_dir / "command-test.txt",
        task_id=task_id,
        round_num=0,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output="ok\n",
        fingerprint=fp,
    )

    from edison.cli.evidence.capture import main as capture_main

    rc = capture_main(
        argparse.Namespace(
            task_id=task_id,
            only=[],
            all=False,
            preset=None,
            session_close=False,
            command_name=None,
            continue_on_failure=False,
            force=False,
            no_lock=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("reusedSnapshot") is True
    assert payload.get("commands") == []


@pytest.mark.qa
def test_evidence_capture_reuses_snapshot_for_only_when_complete(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Minimal CI config for evidence capture (would fail if executed).
    py = sys.executable.replace("\\", "\\\\")
    (isolated_project_env / ".edison" / "config" / "ci.yaml").write_text(
        f"ci:\n  commands:\n    test: \"{py} -c \\\"raise SystemExit(2)\\\"\"\n",
        encoding="utf-8",
    )
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir
    from edison.core.task.workflow import TaskQAWorkflow
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    task_id = "241-wave1-evidence-capture-reuse-only"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    fp = compute_repo_fingerprint(isolated_project_env)
    key = current_snapshot_key(project_root=isolated_project_env)
    snap_dir = snapshot_dir(project_root=isolated_project_env, key=key)
    snap_dir.mkdir(parents=True, exist_ok=True)

    write_command_evidence(
        path=snap_dir / "command-test.txt",
        task_id=task_id,
        round_num=0,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output="ok\n",
        fingerprint=fp,
    )

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
            force=False,
            no_lock=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("reusedSnapshot") is True
    assert payload.get("mode") == "only"
    assert payload.get("commands") == []
