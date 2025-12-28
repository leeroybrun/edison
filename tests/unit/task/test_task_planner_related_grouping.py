from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.entity import EntityMetadata
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository


@pytest.mark.task
def test_task_plan_groups_related_tasks_before_unrelated(isolated_project_env: Path) -> None:
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)

    # Same wave (no depends_on). Prefer grouping related tasks together.
    repo.save(Task(id="A", state=todo, title="A", metadata=EntityMetadata.create(created_by="test")))
    repo.save(
        Task(
            id="B",
            state=todo,
            title="B",
            related=["C"],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )
    repo.save(
        Task(
            id="C",
            state=todo,
            title="C",
            related=["B"],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    from edison.core.task.planning import TaskPlanner

    plan = TaskPlanner(project_root=project_root).build_plan()
    assert len(plan.waves) == 1
    wave_ids = [t.id for t in plan.waves[0].tasks]
    assert wave_ids == ["B", "C", "A"]

