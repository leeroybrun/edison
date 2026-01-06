from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.task
def test_task_repository_rejects_legacy_relationship_keys_to_prevent_data_loss(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    task_id = "010-legacy"
    p = root / ".project" / "tasks" / "todo" / f"{task_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        """---
id: 010-legacy
title: Legacy
parent_id: 010-parent
child_ids: [010-child]
depends_on: [010-dep]
blocks_tasks: [010-blocked]
related: [010-related]
---

# Legacy
""",
        encoding="utf-8",
    )

    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=root)
    with pytest.raises(Exception) as excinfo:
        repo.get(task_id)

    # Fail closed with an actionable hint: tasks must be migrated first.
    assert "legacy" in str(excinfo.value).lower()
