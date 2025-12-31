from __future__ import annotations

from pathlib import Path

import pytest


def _create_session(repo_root: Path, session_id: str, *, state: str) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=repo_root)
    repo.create(Session(id=session_id, state=state, owner="test"))


def test_claim_task_takeover_requires_reason_and_inactive_old_session(
    isolated_project_env: Path,
) -> None:
    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.entity import PersistenceError
    from edison.core.task.workflow import TaskQAWorkflow
    from tests.helpers.fixtures import create_task_file

    workflow_cfg = WorkflowConfig(repo_root=isolated_project_env)
    session_state_active = workflow_cfg.get_initial_state("session")
    wip_state = workflow_cfg.get_semantic_state("task", "wip")

    old_session_id = "sess-old"
    new_session_id = "sess-new"
    task_id = "T-TAKEOVER"

    _create_session(isolated_project_env, old_session_id, state=session_state_active)
    _create_session(isolated_project_env, new_session_id, state=session_state_active)

    create_task_file(isolated_project_env, task_id, state=wip_state, session_id=old_session_id)

    workflow = TaskQAWorkflow(project_root=isolated_project_env)

    # Default behavior remains fail-closed.
    with pytest.raises(PersistenceError):
        workflow.claim_task(task_id, new_session_id)

    # Takeover requires an explicit reason.
    with pytest.raises(PersistenceError):
        workflow.claim_task(task_id, new_session_id, takeover=True)

    # Active old session must block takeover.
    with pytest.raises(PersistenceError):
        workflow.claim_task(task_id, new_session_id, takeover=True, takeover_reason="continuation")

    # Mark old session inactive, then takeover should succeed.
    from edison.core.session.persistence.repository import SessionRepository

    sess_repo = SessionRepository(project_root=isolated_project_env)
    old_session = sess_repo.get(old_session_id)
    assert old_session is not None
    old_session.state = "validated"
    sess_repo.save(old_session)

    claimed = workflow.claim_task(
        task_id,
        new_session_id,
        takeover=True,
        takeover_reason="continuation",
    )
    assert claimed.session_id == new_session_id
