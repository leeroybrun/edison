from __future__ import annotations

import argparse
from pathlib import Path


def test_qa_transition_alias_promotes_waiting_to_todo(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    task_id = "102-wave1-qa-transition-alias"
    TaskRepository(project_root=isolated_project_env).create(
        Task.create(task_id, "Task for QA transition", description="x", state="done")
    )

    qa_repo = QARepository(project_root=isolated_project_env)
    qa_repo.create(
        QARecord(
            id=f"{task_id}-qa",
            task_id=task_id,
            title="QA for task",
            state="waiting",
        )
    )

    from edison.cli.qa.transition import main

    rc = main(
        argparse.Namespace(
            task_id=task_id,
            to="todo",
            status=None,
            session=None,
            dry_run=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    updated = qa_repo.get(f"{task_id}-qa")
    assert updated is not None
    assert updated.state == "todo"
