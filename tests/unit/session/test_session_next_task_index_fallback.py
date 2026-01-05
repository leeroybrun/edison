from __future__ import annotations

from edison.core.config.domains.session import SessionConfig
from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.session.core.models import Session
from edison.core.session.next.compute import compute_next
from edison.core.session.persistence.graph import register_task
from edison.core.session.persistence.repository import SessionRepository


def test_session_next_falls_back_to_session_task_index_when_task_files_missing(
    project_root, monkeypatch
) -> None:
    monkeypatch.chdir(project_root)

    workflow = WorkflowConfig(repo_root=project_root)
    task_wip = workflow.get_semantic_state("task", "wip")

    session_id = "sess-next-fallback-001"
    repo = SessionRepository(project_root=project_root)
    initial_state = SessionConfig(repo_root=project_root).get_initial_session_state()
    repo.create(Session.create(session_id, owner="test", state=initial_state))

    # Register a task event, but do NOT create a task file.
    #
    # Session JSON is not a task index: session-next must only discover tasks from
    # the filesystem (`.project/tasks/...` + session-scoped task dirs).
    register_task(session_id, "missing-task-file-001", owner="test", status=task_wip)

    payload = compute_next(session_id, scope=None, limit=5)

    actions = payload.get("actions") or []
    assert not any(a.get("id") == "task.work" and a.get("recordId") == "missing-task-file-001" for a in actions)
