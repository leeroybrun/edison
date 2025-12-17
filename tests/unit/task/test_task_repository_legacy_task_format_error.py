from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.entity import PersistenceError
from edison.core.task.repository import TaskRepository


def test_task_repository_raises_on_legacy_html_comment_task(isolated_project_env: Path) -> None:
    # Create a legacy-format task (HTML comments, no YAML frontmatter)
    task_id = "101.1-wave1-fix-dashboard-type-errors"
    task_path = isolated_project_env / ".project" / "tasks" / "done" / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(
        "\n".join(
            [
                f"<!-- TaskID: {task_id} -->",
                "<!-- Owner: test -->",
                "<!-- Status: done -->",
                "",
                f"# {task_id}",
                "",
                "Legacy task body",
                "",
            ]
        ),
        encoding="utf-8",
    )

    repo = TaskRepository(project_root=isolated_project_env)

    with pytest.raises(PersistenceError) as exc:
        repo.get(task_id)

    msg = str(exc.value)
    assert "YAML frontmatter" in msg or "migrate" in msg




