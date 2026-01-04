from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.entity import EntityMetadata
from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository


@pytest.mark.task
def test_task_link_force_overwrite_updates_old_parent_inverse_edge(
    isolated_project_env: Path,
) -> None:
    project_root = isolated_project_env
    workflow = WorkflowConfig(repo_root=project_root)
    todo = workflow.get_semantic_state("task", "todo")

    repo = TaskRepository(project_root=project_root)
    repo.save(Task(id="P1", state=todo, title="P1", metadata=EntityMetadata.create(created_by="test")))
    repo.save(Task(id="P2", state=todo, title="P2", metadata=EntityMetadata.create(created_by="test")))
    repo.save(Task(id="C", state=todo, title="C", metadata=EntityMetadata.create(created_by="test")))

    from edison.cli.task.link import main as link_main

    # Initial link: C -> P1.
    assert (
        link_main(
            argparse.Namespace(
                parent_id="P1",
                child_id="C",
                session=None,
                unlink=False,
                force=False,
                json=True,
                repo_root=project_root,
            )
        )
        == 0
    )

    # Force overwrite: C -> P2 (must remove inverse child edge from P1).
    assert (
        link_main(
            argparse.Namespace(
                parent_id="P2",
                child_id="C",
                session=None,
                unlink=False,
                force=True,
                json=True,
                repo_root=project_root,
            )
        )
        == 0
    )

    p1 = repo.get("P1")
    p2 = repo.get("P2")
    c = repo.get("C")
    assert p1 is not None and p2 is not None and c is not None

    assert c.parent_id == "P2"
    assert "C" in (p2.child_ids or [])
    assert "C" not in (p1.child_ids or [])

