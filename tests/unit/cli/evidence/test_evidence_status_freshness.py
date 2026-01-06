from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def _commit_gitignore(repo_root: Path) -> None:
    from edison.core.utils.subprocess import run_with_timeout

    gi = repo_root / ".gitignore"
    gi.write_text(".project/\n.edison/\n", encoding="utf-8")
    run_with_timeout(["git", "add", ".gitignore"], cwd=repo_root, check=True)
    run_with_timeout(["git", "commit", "-m", "Add test gitignore"], cwd=repo_root, check=True)


@pytest.mark.qa
def test_write_command_evidence_includes_fingerprint_fields(
    isolated_project_env: Path,
) -> None:
    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import (
        parse_command_evidence,
        write_command_evidence,
    )
    from edison.core.task.workflow import TaskQAWorkflow

    _commit_gitignore(isolated_project_env)

    task_id = "200-wave1-evidence-fingerprint"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    ev = EvidenceService(task_id=task_id, project_root=isolated_project_env)
    round_dir = ev.ensure_round(1)

    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    fp = compute_repo_fingerprint(isolated_project_env)

    out_path = round_dir / "command-test.txt"
    write_command_evidence(
        path=out_path,
        task_id=task_id,
        round_num=1,
        command_name="test",
        command="python -c \"print('ok')\"",
        cwd=str(isolated_project_env),
        exit_code=0,
        output="ok\n",
        fingerprint=fp,
    )

    parsed = parse_command_evidence(out_path)
    assert parsed is not None
    assert parsed.get("gitHead") == fp.get("gitHead")
    assert parsed.get("gitDirty") == fp.get("gitDirty")
    assert parsed.get("diffHash") == fp.get("diffHash")


@pytest.mark.qa
def test_evidence_status_json_reports_stale_when_repo_changes(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Narrow baseline required evidence to the single command file we will write.
    cfg = isolated_project_env / ".edison" / "config" / "validation.yaml"
    cfg.write_text(
        "validation:\n  evidence:\n    requiredFiles:\n      - command-test.txt\n",
        encoding="utf-8",
    )

    _commit_gitignore(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "201-wave1-evidence-status-stale"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Test", create_qa=False)

    from edison.core.utils.git.fingerprint import compute_repo_fingerprint
    from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir

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

    from edison.cli.evidence.status import main as status_main

    rc = status_main(
        argparse.Namespace(
            task_id=task_id,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    stale = payload.get("staleEvidence") or []
    assert any(e.get("file") == "command-test.txt" and e.get("stale") is False for e in stale)

    # Change repo after evidence capture -> required evidence is now missing for the new fingerprint.
    (isolated_project_env / "README.md").write_text("# changed\n", encoding="utf-8")

    rc2 = status_main(
        argparse.Namespace(
            task_id=task_id,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc2 == 1
    payload2 = json.loads(capsys.readouterr().out)
    assert "command-test.txt" in (payload2.get("missing") or [])
