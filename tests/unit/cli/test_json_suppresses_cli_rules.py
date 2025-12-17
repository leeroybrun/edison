from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_json_mode_suppresses_cli_rules_preamble(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When `--json` is passed, stdout should be parseable JSON without CLI rule noise on stderr."""
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(Task.create("task-json-001", title="JSON status task"))

    from edison.cli._dispatcher import main as cli_main

    code = cli_main(["task", "status", "task-json-001", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    json.loads(captured.out or "{}")
    assert "RULES TO FOLLOW" not in (captured.err or "")
