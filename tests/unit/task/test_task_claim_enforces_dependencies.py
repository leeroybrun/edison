from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.entity import EntityMetadata, PersistenceError
from edison.core.session.core.models import Session
from edison.core.session.persistence.repository import SessionRepository
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository
from edison.core.task.workflow import TaskQAWorkflow
from edison.core.config.domains.workflow import WorkflowConfig


@pytest.mark.task
def test_claim_task_blocks_when_depends_on_not_satisfied(isolated_project_env: Path) -> None:
    project_root = isolated_project_env
    session_id = "test-session-claim-deps"

    # Create a session to claim into.
    session_repo = SessionRepository(project_root)
    session_repo.create(Session.create(session_id, state="wip"))

    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)

    dep = Task(
        id="dep-todo",
        state=todo,
        title="Dependency todo",
        metadata=EntityMetadata.create(created_by="test"),
    )
    task = Task(
        id="task-with-dep",
        state=todo,
        title="Task with dependency",
        relationships=[{"type": "depends_on", "target": "dep-todo"}],
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(dep)
    repo.save(task)

    with pytest.raises(PersistenceError):
        TaskQAWorkflow(project_root).claim_task("task-with-dep", session_id)


@pytest.mark.task
def test_claim_task_allows_when_depends_on_satisfied(isolated_project_env: Path) -> None:
    project_root = isolated_project_env
    session_id = "test-session-claim-deps-2"

    session_repo = SessionRepository(project_root)
    session_repo.create(Session.create(session_id, state="wip"))

    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")
    done = workflow.get_semantic_state("task", "done")

    repo = TaskRepository(project_root=project_root)
    dep_done = Task(
        id="dep-done",
        state=done,
        title="Dependency done",
        metadata=EntityMetadata.create(created_by="test"),
    )
    task = Task(
        id="task-with-dep-2",
        state=todo,
        title="Task with dependency",
        relationships=[{"type": "depends_on", "target": "dep-done"}],
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(dep_done)
    repo.save(task)

    claimed = TaskQAWorkflow(project_root).claim_task("task-with-dep-2", session_id)
    assert claimed.state == str(workflow.get_semantic_state("task", "wip"))
