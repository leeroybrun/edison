from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.entity import EntityMetadata
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository


@pytest.mark.task
def test_task_ready_list_uses_dependency_readiness(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = WorkflowConfig(repo_root=isolated_project_env)
    todo = workflow.get_semantic_state("task", "todo")
    done = workflow.get_semantic_state("task", "done")

    repo = TaskRepository(project_root=isolated_project_env)

    dep_done = Task(
        id="dep-done",
        state=done,
        title="Dependency done",
        metadata=EntityMetadata.create(created_by="test"),
    )
    dep_todo = Task(
        id="dep-todo",
        state=todo,
        title="Dependency todo",
        metadata=EntityMetadata.create(created_by="test"),
    )
    ready = Task(
        id="task-ready",
        state=todo,
        title="Ready",
        depends_on=["dep-done"],
        metadata=EntityMetadata.create(created_by="test"),
    )
    blocked = Task(
        id="task-blocked",
        state=todo,
        title="Blocked",
        depends_on=["dep-todo"],
        metadata=EntityMetadata.create(created_by="test"),
    )
    missing = Task(
        id="task-missing",
        state=todo,
        title="Missing dep",
        depends_on=["dep-missing"],
        metadata=EntityMetadata.create(created_by="test"),
    )

    for t in (dep_done, dep_todo, ready, blocked, missing):
        repo.save(t)

    from edison.cli.task.ready import main as ready_main

    args = argparse.Namespace(
        record_id=None,
        session=None,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = ready_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)
    ids = {t["id"] for t in data["tasks"]}

    assert "task-ready" in ids
    assert "task-blocked" not in ids
    assert "task-missing" not in ids


@pytest.mark.task
def test_task_blocked_lists_unmet_dependencies(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = WorkflowConfig(repo_root=isolated_project_env)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=isolated_project_env)
    blocked = Task(
        id="task-blocked-2",
        state=todo,
        title="Blocked 2",
        depends_on=["dep-missing-2"],
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(blocked)

    from edison.cli.task.blocked import main as blocked_main

    args = argparse.Namespace(
        record_id=None,
        session=None,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = blocked_main(args)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    entry = data["tasks"][0]
    assert entry["id"] == "task-blocked-2"
    assert entry["unmetDependencies"][0]["id"] == "dep-missing-2"

