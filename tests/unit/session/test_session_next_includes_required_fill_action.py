from __future__ import annotations

from pathlib import Path

from edison.core.session.core.models import Session
from edison.core.session.next.compute import compute_next
from edison.core.session.persistence.repository import SessionRepository
from edison.core.task.workflow import TaskQAWorkflow


def test_session_next_includes_fill_required_sections_action_for_incomplete_task(
    isolated_project_env: Path, monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    session_id = "sess-required-fill-001"
    SessionRepository(project_root=isolated_project_env).create(Session.create(session_id, owner="test", state="active"))

    task_id = "001-required-fill"
    TaskQAWorkflow(project_root=isolated_project_env).create_task(
        task_id=task_id,
        title="Required fill task",
        session_id=session_id,
        create_qa=False,
    )

    payload = compute_next(session_id, scope=None, limit=25)
    actions = payload.get("actions") or []

    assert any(
        a.get("id") == "task.fill_required_sections"
        and a.get("recordId") == task_id
        and a.get("cmd") == ["edison", "task", "show", task_id]
        for a in actions
    )

