from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.session
def test_session_next_includes_session_close_preflight_checklist_when_no_wip_tasks(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.session.next.compute import compute_next

    session_id = "sess-close-preflight-1"
    task_id = "160-wave1-close-preflight"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="active"))

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_done = wf.get_semantic_state("task", "done")
    qa_done = wf.get_semantic_state("qa", "done")

    TaskRepository(isolated_project_env).save(
        Task.create(
            task_id=task_id,
            title="Done task",
            description="",
            session_id=session_id,
            owner="tester",
            state=task_done,
        )
    )
    QARepository(project_root=isolated_project_env).save(
        QARecord.create(
            qa_id=f"{task_id}-qa",
            task_id=task_id,
            title="QA",
            session_id=session_id,
            state=qa_done,
        )
    )

    payload = compute_next(session_id, scope="session", limit=50)
    actions = payload.get("actions") or []
    close_preflight = next((a for a in actions if a.get("id") == "session.close_preflight"), None)
    assert close_preflight is not None
    checklist = close_preflight.get("checklist")
    assert isinstance(checklist, dict)
    assert checklist.get("kind") == "session_close_preflight"
