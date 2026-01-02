from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_task_split_prints_required_fill_next_steps(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(Task.create("900-parent", "Parent task", state="todo"))

    from edison.cli.task.split import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["900-parent", "--count", "1", "--prefix", "part1", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Next steps:" in out
    assert "Fill required sections" in out

