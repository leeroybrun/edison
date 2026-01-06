from __future__ import annotations

from edison.core.entity import EntityMetadata
from edison.core.task.models import Task


def _task(**kwargs) -> Task:
    return Task(
        id="T",
        state="todo",
        title="T",
        metadata=EntityMetadata.create(created_by="test"),
        **kwargs,
    )


def test_task_relationship_properties_are_derived_from_relationship_edges() -> None:
    task = _task(
        relationships=[
            {"type": "parent", "target": "P"},
            {"type": "child", "target": "C"},
            {"type": "depends_on", "target": "D"},
            {"type": "blocks", "target": "B"},
            {"type": "related", "target": "R"},
            {"type": "bundle_root", "target": "ROOT"},
        ]
    )

    assert task.parent_id == "P"
    assert task.child_ids == ["C"]
    assert task.depends_on == ["D"]
    assert task.blocks_tasks == ["B"]
    assert task.related == ["R"]
    assert task.bundle_root == "ROOT"

