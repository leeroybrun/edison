from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.task
def test_task_repository_ignores_frontmatter_status_and_derives_state_from_path(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    task_id = "300.1.1.2-wave2-fix-leak-check-test"

    p = root / ".project" / "tasks" / "todo" / f"{task_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        """---
id: 300.1.1.2-wave2-fix-leak-check-test
title: Test
owner: someone
status: wip
state: wip
---

# Test
""",
        encoding="utf-8",
    )

    from edison.core.task.repository import TaskRepository

    task = TaskRepository(project_root=root).get(task_id)
    assert task is not None
    assert task.state == "todo"
