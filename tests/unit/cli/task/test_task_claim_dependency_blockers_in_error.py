from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_claim_json_includes_dependency_blockers_on_failure(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.entity import EntityMetadata
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    session_id = "sess-claim-blocked"
    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = WorkflowConfig(repo_root=isolated_project_env)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=isolated_project_env)
    repo.save(
        Task(
            id="dep-todo",
            state=todo,
            title="Dependency todo",
            metadata=EntityMetadata.create(created_by="test"),
        )
    )
    repo.save(
        Task(
            id="task-main",
            state=todo,
            title="Main task",
            relationships=[{"type": "depends_on", "target": "dep-todo"}],
            metadata=EntityMetadata.create(created_by="test"),
        )
    )

    from edison.cli.task.claim import main as claim_main

    rc = claim_main(
        argparse.Namespace(
            record_id="task-main",
            session=session_id,
            type="task",
            owner=None,
            status=None,
            takeover=False,
            reclaim=False,
            reason=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 1

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("error") == "claim_error"
    assert payload.get("blockedBy"), "Expected dependency blockers to be surfaced"
    assert payload["blockedBy"][0]["dependencyId"] == "dep-todo"

