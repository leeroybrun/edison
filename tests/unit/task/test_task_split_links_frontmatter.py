from __future__ import annotations

import argparse
from pathlib import Path

from edison.core.task import TaskQAWorkflow, TaskRepository
from edison.cli.task import split as split_cli


def test_task_split_persists_parent_child_links(isolated_project_env: Path) -> None:
    repo = isolated_project_env

    workflow = TaskQAWorkflow(project_root=repo)
    parent_id = "T-100"
    workflow.create_task(
        task_id=parent_id,
        title="Parent",
        create_qa=False,
    )

    args = argparse.Namespace(
        task_id=parent_id,
        count=2,
        prefix=None,
        dry_run=False,
        json=True,
        repo_root=str(repo),
    )
    assert split_cli.main(args) == 0

    task_repo = TaskRepository(project_root=repo)
    parent = task_repo.get(parent_id)
    assert parent is not None
    assert set(parent.child_ids) == {f"{parent_id}.1-part1", f"{parent_id}.2-part2"}

    c1 = task_repo.get(f"{parent_id}.1-part1")
    c2 = task_repo.get(f"{parent_id}.2-part2")
    assert c1 is not None and c2 is not None
    assert c1.parent_id == parent_id
    assert c2.parent_id == parent_id


def test_task_split_uses_next_available_child_number(isolated_project_env: Path) -> None:
    """Splitting twice should not collide with existing child tasks."""
    repo = isolated_project_env

    workflow = TaskQAWorkflow(project_root=repo)
    parent_id = "T-200"
    workflow.create_task(
        task_id=parent_id,
        title="Parent",
        create_qa=False,
    )

    existing_child_id = f"{parent_id}.1-part1"
    workflow.create_task(
        task_id=existing_child_id,
        title="Existing child",
        create_qa=False,
    )

    task_repo = TaskRepository(project_root=repo)
    parent = task_repo.get(parent_id)
    child = task_repo.get(existing_child_id)
    assert parent is not None and child is not None
    parent.child_ids = [existing_child_id]
    child.parent_id = parent_id
    task_repo.save(child)
    task_repo.save(parent)

    args = argparse.Namespace(
        task_id=parent_id,
        count=2,
        prefix=None,
        dry_run=False,
        json=True,
        repo_root=str(repo),
    )
    assert split_cli.main(args) == 0

    updated_parent = task_repo.get(parent_id)
    assert updated_parent is not None
    assert set(updated_parent.child_ids) == {
        existing_child_id,
        f"{parent_id}.2-part2",
        f"{parent_id}.3-part3",
    }
