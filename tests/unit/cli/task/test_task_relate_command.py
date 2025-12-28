from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.entity import EntityMetadata
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository


@pytest.mark.task
def test_task_relate_adds_bidirectional_related_links(isolated_project_env: Path) -> None:
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    repo.save(Task(id="A", state=todo, title="A", metadata=EntityMetadata.create(created_by="test")))
    repo.save(Task(id="B", state=todo, title="B", metadata=EntityMetadata.create(created_by="test")))

    from edison.cli.task.relate import main as relate_main

    args = argparse.Namespace(
        task_a="A",
        task_b="B",
        remove=False,
        json=False,
        repo_root=project_root,
    )
    rc = relate_main(args)
    assert rc == 0

    a = repo.get("A")
    b = repo.get("B")
    assert a is not None and b is not None
    assert "B" in (a.related or [])
    assert "A" in (b.related or [])

