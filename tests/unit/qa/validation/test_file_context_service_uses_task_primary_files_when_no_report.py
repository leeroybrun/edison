from __future__ import annotations

from pathlib import Path

from edison.core.context.files import FileContextService


def test_file_context_service_prefers_task_primary_files_when_no_report(
    isolated_project_env: Path,
) -> None:
    repo = isolated_project_env

    # Create a task file with Primary Files / Areas.
    task_id = "t-primary"
    task_path = repo / ".project" / "tasks" / "todo" / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(
        """
---
id: t-primary
title: Primary Files Task
---

## Primary Files / Areas
- src/app.py
- src/lib/util.py
""".lstrip(),
        encoding="utf-8",
    )

    ctx = FileContextService(project_root=repo).get_for_task(task_id, session_id="sid-any")
    assert ctx.source == "task_spec"
    assert "src/app.py" in ctx.all_files
    assert "src/lib/util.py" in ctx.all_files

