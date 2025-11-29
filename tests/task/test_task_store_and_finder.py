"""Integration smoke tests for the new ``lib.task`` namespace.

These tests exercise the store and finder helpers end-to-end using an
isolated repository rooted at ``tmp_path``. They ensure configuration-driven
paths are respected and that task discovery works without the legacy
``task`` module.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

from pathlib import Path

import importlib

def _bootstrap_repo(repo: Path) -> None:
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": []},
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "todo"}]},
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": []},
                    },
                },
            }
        },
    )
    write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                },
                "defaults": {
                    "ownerPrefix": "- **Owner:** ",
                    "validatorOwnerPrefix": "- **Validator Owner:** ",
                    "statusPrefix": "- **Status:** ",
                    "claimedPrefix": "  - **Claimed At:** ",
                    "lastActivePrefix": "  - **Last Active:** ",
                    "continuationPrefix": "  - **Continuation ID:** ",
                },
            }
        },
    )

def test_create_and_find_task(tmp_path, monkeypatch):
    repo = tmp_path
    _bootstrap_repo(repo)

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver

    resolver._PROJECT_ROOT_CACHE = None

    import edison.core.task.paths as paths
    paths = importlib.reload(paths)

    for d in [*paths.get_task_dirs().values(), *paths.get_qa_dirs().values(), *paths.get_session_dirs().values()]:
        d.mkdir(parents=True, exist_ok=True)

    from edison.core.task.repository import TaskRepository
    from edison.core.task.models import Task
    from edison.core.entity import EntityMetadata

    # Create a task and ensure it lands in the configured todo queue
    repo = TaskRepository(project_root=repo)
    task = Task(
        id="T-123",
        state="todo",
        title="Decompose god module",
        description="desc",
        metadata=EntityMetadata.create(),
    )
    created_task = repo.create(task)

    # Find the task file
    path = repo._find_entity_path("T-123")
    assert path is not None
    assert path.exists()
    assert path.parent == paths.get_task_dirs().get("todo")

    # Repository should locate the task
    found = repo.get("T-123")
    assert found is not None
    assert found.id == "T-123"

    # List all tasks
    all_tasks = repo.list_all()
    ids = {t.id for t in all_tasks}
    assert "T-123" in ids
