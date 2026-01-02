from __future__ import annotations

import argparse
from pathlib import Path


def test_task_transition_alias_transitions_task_when_forced(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(
        Task.create(
            "101-wave1-transition-alias",
            "Test task transition alias",
            description="Test task transition alias",
            state="todo",
        )
    )

    from edison.cli.task.transition import main

    rc = main(
        argparse.Namespace(
            record_id="101-wave1-transition-alias",
            to="wip",
            status=None,
            reason="test",
            type="task",
            dry_run=False,
            force=True,
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    updated = repo.get("101-wave1-transition-alias")
    assert updated is not None
    assert updated.state == "wip"

