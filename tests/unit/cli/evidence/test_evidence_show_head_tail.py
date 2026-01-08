from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_evidence_show_tail_clips_output_in_json(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    cfg = isolated_project_env / ".edison" / "config" / "validation.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "242-wave1-evidence-show-tail"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    fp = compute_repo_fingerprint(isolated_project_env)
    key = current_snapshot_key(project_root=isolated_project_env)
    snap_dir = snapshot_dir(project_root=isolated_project_env, key=key)
    snap_dir.mkdir(parents=True, exist_ok=True)

    output = "\n".join(["l1", "l2", "l3", "l4"]) + "\n"
    write_command_evidence(
        path=snap_dir / "command-test.txt",
        task_id=task_id,
        round_num=0,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output=output,
        fingerprint=fp,
    )

    from edison.cli.evidence.show import main as show_main

    rc = show_main(
        argparse.Namespace(
            task_id=task_id,
            filename=None,
            command_name="test",
            raw=False,
            head=None,
            tail=2,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("output") == "l3\nl4"
    assert payload.get("totalLines") == 4
    assert payload.get("shownLines") == 2
    assert payload.get("truncated") is True

