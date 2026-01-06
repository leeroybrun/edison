from __future__ import annotations

import pytest
from pathlib import Path


@pytest.mark.session
def test_register_task_does_not_persist_session_task_index(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.graph import register_qa, register_task
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.utils.io import read_json

    session_id = "s-no-index"
    task_id = "T-1"
    qa_id = f"{task_id}-qa"

    repo = SessionRepository(project_root=isolated_project_env)
    repo.save(Session.create(session_id=session_id, owner="tester"))

    register_task(session_id, task_id, owner="tester", status="wip", qa_id=qa_id)
    register_qa(session_id, task_id, qa_id, status="todo", round_no=1)

    path = repo._find_entity_path(session_id)
    assert path is not None

    data = read_json(path)
    assert data.get("tasks") == {}
    assert data.get("qa") == {}

