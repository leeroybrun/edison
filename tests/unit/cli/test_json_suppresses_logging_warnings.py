from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest


def test_json_mode_disables_warning_logging(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--json` should suppress lastResort WARNING noise without globally disabling logging."""
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(Task.create("task-json-002", title="JSON logging task"))

    from edison.cli._dispatcher import main as cli_main

    logging.disable(logging.NOTSET)
    assert logging.getLogger().isEnabledFor(logging.WARNING)

    try:
        code = cli_main(["task", "status", "task-json-002", "--json"])
        captured = capsys.readouterr()
        assert code == 0
        json.loads(captured.out or "{}")
        # WARNING should remain enabled; JSON mode should prevent stderr pollution via handlers,
        # not by disabling logging globally.
        assert logging.getLogger().isEnabledFor(logging.WARNING)
    finally:
        logging.disable(logging.NOTSET)
