from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.session
def test_session_next_includes_qa_validate_preflight_checklist(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository

    session_id = "sess-qa-preflight-1"
    task_id = "151-wave1-qa-preflight"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="active"))

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_done = wf.get_semantic_state("task", "done")
    qa_todo = wf.get_semantic_state("qa", "todo")

    task = Task.create(
        task_id=task_id,
        title="Test",
        description="",
        session_id=session_id,
        owner="tester",
        state=task_done,
    )
    TaskRepository(isolated_project_env).save(task)

    qa = QARecord.create(
        qa_id=f"{task_id}-qa",
        task_id=task_id,
        title="QA",
        session_id=session_id,
        state=qa_todo,
    )
    QARepository(project_root=isolated_project_env).save(qa)

    from edison.core.session.next.compute import compute_next

    payload = compute_next(session_id, scope="qa", limit=50)
    actions = payload.get("actions") or []
    qa_start = next((a for a in actions if a.get("id") == "qa.promote.wip"), None)
    assert qa_start is not None
    assert "qa" in (qa_start.get("cmd") or [])
    checklist = qa_start.get("checklist")
    assert isinstance(checklist, dict)
    assert checklist.get("kind") == "qa_validate_preflight"
