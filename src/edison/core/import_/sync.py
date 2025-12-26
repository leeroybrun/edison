"""Shared sync helpers for importing external work items as Edison tasks.

Importers should be "thin":
- Parse external artifacts into typed items
- Render Edison task title/description/tags
- Use sync_items_to_tasks to create/update/flag tasks consistently
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Set, TypeVar

from edison.core.task.models import Task
from edison.core.task.repository import TaskRepository

TItem = TypeVar("TItem")
TKey = TypeVar("TKey")


@dataclass
class SyncResult:
    """Result of import/sync operation."""

    created: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    flagged: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def sync_items_to_tasks(
    items: Sequence[TItem],
    *,
    task_repo: TaskRepository,
    item_key: Callable[[TItem], TKey],
    build_task: Callable[[TItem], Task],
    update_task: Callable[[Task, TItem], None],
    is_managed_task: Callable[[Task], bool],
    task_key: Callable[[Task], TKey],
    removed_tag: str,
    create_qa: bool,
    qa_created_by: str,
    dry_run: bool,
    project_root: Optional[Path],
    updatable_states: Set[str] | None = None,
) -> SyncResult:
    """Sync external items into Edison tasks.

    Precedence rules are importer-specific via callbacks; core mechanics are shared.
    """
    result = SyncResult()

    if updatable_states is None:
        updatable_states = {"todo"}

    managed_tasks = [t for t in task_repo.find_all() if is_managed_task(t)]
    existing_by_key = {task_key(t): t for t in managed_tasks}
    desired_keys = {item_key(i) for i in items}

    for item in items:
        key = item_key(item)
        new_task = build_task(item)
        if key in existing_by_key:
            existing = existing_by_key[key]
            if existing.state not in updatable_states:
                result.skipped.append(new_task.id)
                continue
            if not dry_run:
                update_task(existing, item)
                task_repo.save(existing)
            result.updated.append(new_task.id)
        else:
            if not dry_run:
                task_repo.save(new_task)
                if create_qa:
                    create_qa_record(
                        task_id=new_task.id,
                        project_root=project_root,
                        created_by=qa_created_by,
                    )
            result.created.append(new_task.id)

    # Flag removed
    for key, existing in existing_by_key.items():
        if key in desired_keys:
            continue
        if not dry_run:
            flag_task_as_removed(task_repo, existing, removed_tag=removed_tag)
        result.flagged.append(existing.id)

    return result


def flag_task_as_removed(repo: TaskRepository, task: Task, *, removed_tag: str) -> None:
    if removed_tag not in task.tags:
        task.tags.append(removed_tag)
        repo.save(task)


def create_qa_record(*, task_id: str, project_root: Optional[Path], created_by: str) -> None:
    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.entity import EntityMetadata

    qa_repo = QARepository(project_root)
    qa = QARecord(
        id=f"{task_id}-qa",
        task_id=task_id,
        state="waiting",
        title=f"QA {task_id}",
        metadata=EntityMetadata.create(created_by=created_by),
    )
    qa_repo.save(qa)


__all__ = ["SyncResult", "sync_items_to_tasks", "flag_task_as_removed", "create_qa_record"]
