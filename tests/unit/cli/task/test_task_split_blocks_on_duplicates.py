from __future__ import annotations

import argparse
from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_task_split_can_block_when_duplicate_check_configured(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(Task.create("700-parent", "Parent task", state="todo"))

    # Create an existing task that matches the child title ("Part 1").
    repo.create(Task.create("701-existing", "Part 1", state="todo"))

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "tasks.yaml",
        {"tasks": {"similarity": {"preCreate": {"enabled": True, "action": "block", "threshold": 0.1}}}},
    )
    reset_edison_caches()

    from edison.cli.task.split import main

    rc = main(
        argparse.Namespace(
            task_id="700-parent",
            count=1,
            prefix="part1",
            dry_run=False,
            force=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 1

