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
def test_task_blocked_treats_session_scoped_dependency_as_unmet_for_global_tasks(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Global backlog readiness should not be satisfied by tasks that only exist in another session."""
    monkeypatch.chdir(isolated_project_env)

    workflow = WorkflowConfig(repo_root=isolated_project_env)
    todo = workflow.get_semantic_state("task", "todo")
    done = workflow.get_semantic_state("task", "done")

    repo = TaskRepository(project_root=isolated_project_env)

    dep = Task(
        id="dep-session",
        state=done,
        title="Dependency in session",
        session_id="sess-1",
        metadata=EntityMetadata.create(created_by="test"),
    )
    main = Task(
        id="main-global",
        state=todo,
        title="Main task",
        relationships=[{"type": "depends_on", "target": "dep-session"}],
        metadata=EntityMetadata.create(created_by="test"),
    )
    repo.save(dep)
    repo.save(main)

    from edison.cli.task.blocked import main as blocked_main

    rc = blocked_main(
        argparse.Namespace(
            record_id="main-global",
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload["blocked"] is True
    assert payload["unmetDependencies"][0]["id"] == "dep-session"
    assert "session" in (payload["unmetDependencies"][0]["reason"] or "").lower()

