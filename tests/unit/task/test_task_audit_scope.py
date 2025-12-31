from __future__ import annotations

import textwrap
from pathlib import Path


def _write_task(path: Path, *, task_id: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            ---
            id: {task_id}
            title: "{title}"
            ---
            # {title}

            ## Files to Create/Modify

            ```text
            src/example.py
            ```
            """
        ),
        encoding="utf-8",
    )


def test_task_audit_default_scans_global_only(isolated_project_env):
    from edison.core.task.audit import audit_tasks

    _write_task(Path(".project/tasks/todo/t-1.md"), task_id="t-1", title="Global task")

    report = audit_tasks(project_root=Path.cwd(), include_session_tasks=False)
    payload = report.to_dict()

    assert payload["taskCount"] == 1
    assert payload["includeSessionTasks"] is False


def test_task_audit_include_session_tasks_scans_sessions(isolated_project_env):
    from edison.core.task.audit import audit_tasks

    _write_task(Path(".project/tasks/todo/t-1.md"), task_id="t-1", title="Global task")
    _write_task(
        Path(".project/sessions/wip/sess-1/tasks/todo/t-2.md"),
        task_id="t-2",
        title="Session task",
    )

    report = audit_tasks(project_root=Path.cwd(), include_session_tasks=True)
    payload = report.to_dict()

    assert payload["taskCount"] == 2
    assert payload["includeSessionTasks"] is True
    assert "tasksRootsScanned" in payload

