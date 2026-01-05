from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_new_json_includes_qa_next_steps(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.cli.task.new import main as task_new_main

    rc = task_new_main(
        argparse.Namespace(
            task_id="901",
            wave="wave1",
            slug="contract-task",
            task_type="feature",
            owner=None,
            session=None,
            parent=None,
            continuation_id=None,
            force=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "created"
    assert payload["qaId"].endswith("-qa")
    assert payload["qaCreated"] is True
    assert payload["qaPath"].startswith(".project/")
    assert isinstance(payload["nextSteps"], list) and payload["nextSteps"]

