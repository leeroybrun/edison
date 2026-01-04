from __future__ import annotations

from edison.core.config.domains.session import SessionConfig
from edison.core.session.core.models import Session
from edison.core.session.next.compute import compute_next
from edison.core.session.persistence.repository import SessionRepository


def test_session_next_includes_session_start_checklist_for_new_session(project_root, monkeypatch):
    monkeypatch.chdir(project_root)

    session_id = "sess-start-checklist"
    repo = SessionRepository(project_root=project_root)
    initial_state = SessionConfig(repo_root=project_root).get_initial_session_state()
    repo.create(Session.create(session_id, owner="test", state=initial_state))

    payload = compute_next(session_id, scope=None, limit=5)
    actions = payload.get("actions") or []
    assert isinstance(actions, list) and actions

    start = actions[0]
    assert start.get("id") == "session.start_checklist"
    checklist = start.get("checklist") or {}
    assert checklist.get("kind") == "session_start"
    assert "items" in checklist

