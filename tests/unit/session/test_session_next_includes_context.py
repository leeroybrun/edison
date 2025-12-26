import json

from edison.core.config.domains.session import SessionConfig
from edison.core.session.core.models import Session
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.next.compute import compute_next


def test_session_next_payload_includes_context(project_root, monkeypatch):
    monkeypatch.chdir(project_root)

    session_id = "sess-1"
    repo = SessionRepository(project_root=project_root)
    initial_state = SessionConfig(repo_root=project_root).get_initial_session_state()
    repo.create(Session.create(session_id, owner="test", state=initial_state))

    payload = compute_next(session_id, scope=None, limit=5)

    assert "context" in payload
    assert payload["context"]["isEdisonProject"] is True
    assert payload["context"]["projectRoot"] == str(project_root)
    assert payload["context"]["sessionId"] == session_id

