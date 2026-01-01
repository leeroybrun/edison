from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def test_evidence_init_creates_round_and_metadata(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_id = "task-evidence-init-001"

    from edison.cli.evidence.init import main as init_main

    args = argparse.Namespace(
        task_id=task_id,
        round=1,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = init_main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("taskId") == task_id
    assert payload.get("round") == 1

    evidence_root = isolated_project_env / ".project" / "qa" / "validation-evidence" / task_id
    assert (evidence_root / "round-1").exists()
    assert (evidence_root / "metadata.json").exists()

