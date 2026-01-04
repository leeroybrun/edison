from __future__ import annotations

from pathlib import Path

import pytest


def _create_task(root: Path, task_id: str) -> None:
    from edison.core.task.workflow import TaskQAWorkflow

    TaskQAWorkflow(project_root=root).create_task(
        task_id=task_id,
        title=task_id,
        session_id=None,
        create_qa=False,
    )


@pytest.mark.task
def test_task_relationship_service_add_depends_on_creates_inverse_blocks(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    a = "010-a"
    b = "010-b"
    _create_task(root, a)
    _create_task(root, b)

    from edison.core.task.relationships.service import TaskRelationshipService

    svc = TaskRelationshipService(project_root=root)
    svc.add(task_id=a, rel_type="depends_on", target_id=b)

    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=root)
    a_task = repo.get(a)
    b_task = repo.get(b)
    assert a_task is not None and b_task is not None

    a_edges = {(e["type"], e["target"]) for e in (getattr(a_task, "relationships", []) or [])}
    b_edges = {(e["type"], e["target"]) for e in (getattr(b_task, "relationships", []) or [])}

    assert ("depends_on", b) in a_edges
    assert ("blocks", a) in b_edges


@pytest.mark.task
def test_task_relationship_service_add_related_is_symmetric(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    a = "010-rel-a"
    b = "010-rel-b"
    _create_task(root, a)
    _create_task(root, b)

    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.repository import TaskRepository

    svc = TaskRelationshipService(project_root=root)
    svc.add(task_id=a, rel_type="related", target_id=b)

    repo = TaskRepository(project_root=root)
    a_task = repo.get(a)
    b_task = repo.get(b)
    assert a_task is not None and b_task is not None

    a_edges = {(e["type"], e["target"]) for e in (getattr(a_task, "relationships", []) or [])}
    b_edges = {(e["type"], e["target"]) for e in (getattr(b_task, "relationships", []) or [])}

    assert ("related", b) in a_edges
    assert ("related", a) in b_edges


@pytest.mark.task
def test_task_relationship_service_single_parent_is_enforced_fail_closed(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    parent1 = "010-parent-1"
    parent2 = "010-parent-2"
    child = "010-child"
    _create_task(root, parent1)
    _create_task(root, parent2)
    _create_task(root, child)

    from edison.core.entity import PersistenceError
    from edison.core.task.relationships.service import TaskRelationshipService

    svc = TaskRelationshipService(project_root=root)
    svc.add(task_id=child, rel_type="parent", target_id=parent1)

    with pytest.raises(PersistenceError):
        svc.add(task_id=child, rel_type="parent", target_id=parent2)


@pytest.mark.task
def test_task_relationship_service_bundle_root_is_single_target(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    root1 = "010-bundle-root-1"
    root2 = "010-bundle-root-2"
    member = "010-bundle-member"
    _create_task(root, root1)
    _create_task(root, root2)
    _create_task(root, member)

    from edison.core.entity import PersistenceError
    from edison.core.task.relationships.service import TaskRelationshipService

    svc = TaskRelationshipService(project_root=root)
    svc.add(task_id=member, rel_type="bundle_root", target_id=root1)
    with pytest.raises(PersistenceError):
        svc.add(task_id=member, rel_type="bundle_root", target_id=root2)


@pytest.mark.task
def test_task_relationship_service_remove_related_is_symmetric(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    a = "010-rel-rm-a"
    b = "010-rel-rm-b"
    _create_task(root, a)
    _create_task(root, b)

    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.repository import TaskRepository

    svc = TaskRelationshipService(project_root=root)
    svc.add(task_id=a, rel_type="related", target_id=b)
    svc.remove(task_id=a, rel_type="related", target_id=b)

    repo = TaskRepository(project_root=root)
    a_task = repo.get(a)
    b_task = repo.get(b)
    assert a_task is not None and b_task is not None

    a_edges = {(e["type"], e["target"]) for e in (getattr(a_task, "relationships", []) or [])}
    b_edges = {(e["type"], e["target"]) for e in (getattr(b_task, "relationships", []) or [])}

    assert ("related", b) not in a_edges
    assert ("related", a) not in b_edges
