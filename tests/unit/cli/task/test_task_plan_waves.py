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
def test_task_waves_emits_parallelizable_waves(isolated_project_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")
    done = workflow.get_semantic_state("task", "done")

    repo = TaskRepository(project_root=project_root)

    # Wave 1: A (no deps) and F (dep satisfied outside plan set).
    repo.save(Task(id="A", state=todo, title="A", metadata=EntityMetadata.create(created_by="test")))
    repo.save(Task(id="E", state=done, title="E", metadata=EntityMetadata.create(created_by="test")))
    repo.save(
        Task(
            id="F",
            state=todo,
            title="F",
            relationships=[{"type": "depends_on", "target": "E"}],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    # Wave 2: B and C depend on A.
    repo.save(
        Task(
            id="B",
            state=todo,
            title="B",
            relationships=[{"type": "depends_on", "target": "A"}],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )
    repo.save(
        Task(
            id="C",
            state=todo,
            title="C",
            relationships=[{"type": "depends_on", "target": "A"}],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    # Wave 3: D depends on B and C.
    repo.save(
        Task(
            id="D",
            state=todo,
            title="D",
            relationships=[
                {"type": "depends_on", "target": "B"},
                {"type": "depends_on", "target": "C"},
            ],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    from edison.cli.task.waves import main as waves_main

    args = argparse.Namespace(
        session=None,
        json=True,
        repo_root=project_root,
    )
    rc = waves_main(args)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    waves = {w["wave"]: {t["id"] for t in w["tasks"]} for w in data["waves"]}

    assert waves[1] == {"A", "F"}
    assert waves[2] == {"B", "C"}
    assert waves[3] == {"D"}
    assert data["blocked"] == []


@pytest.mark.task
def test_task_waves_lists_tasks_blocked_by_missing_dependencies(isolated_project_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    repo.save(
        Task(
            id="G",
            state=todo,
            title="G",
            relationships=[{"type": "depends_on", "target": "MISSING"}],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    from edison.cli.task.waves import main as waves_main

    args = argparse.Namespace(
        session=None,
        json=True,
        repo_root=project_root,
    )
    rc = waves_main(args)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    assert data["waves"] == []
    assert data["blocked"][0]["id"] == "G"
    assert data["blocked"][0]["unmetDependencies"][0]["id"] == "MISSING"


@pytest.mark.task
def test_task_waves_excludes_session_tasks_by_default(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Backlog waves should be computed from global tasks unless a session is requested."""
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)

    # Global task (in `.project/tasks/...`).
    repo.save(Task(id="GLOBAL", state=todo, title="Global", metadata=EntityMetadata.create(created_by="test")))

    # Session-scoped task (in the session directory tree). A real session record is not required
    # for this behavior; the file existing is enough for TaskIndex scanning.
    repo.save(
        Task(
            id="SESSION",
            state=todo,
            title="Session task",
            session_id="sess-test-123",
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    from edison.cli.task.waves import main as waves_main

    args = argparse.Namespace(
        session=None,
        json=True,
        repo_root=project_root,
    )
    rc = waves_main(args)
    assert rc == 0

    data = json.loads(capsys.readouterr().out)
    scheduled = {t["id"] for w in data["waves"] for t in w["tasks"]}
    assert "GLOBAL" in scheduled
    assert "SESSION" not in scheduled
