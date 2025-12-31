from __future__ import annotations

from contextlib import contextmanager

from edison.core.session.lifecycle import verify as verify_mod
from edison.core.session.lifecycle.verify import verify_session_health
from edison.core.task import TaskRepository


def test_verify_session_health_is_readonly(isolated_project_env, monkeypatch):
    """verify_session_health must be a diagnostic check with no side effects."""

    @contextmanager
    def _noop_in_session_worktree(_session_id: str):
        yield

    monkeypatch.setattr(
        verify_mod.SessionContext,
        "in_session_worktree",
        staticmethod(_noop_in_session_worktree),
    )
    monkeypatch.setattr(verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid})
    monkeypatch.setattr(TaskRepository, "find_by_session", lambda _self, _sid: [])

    def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
        return {"actions": [], "blockers": [], "reportsMissing": []}

    monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

    # Fail-closed: verify must not restore records or transition state.
    def _boom_restore(_sid: str):
        raise AssertionError("verify_session_health must not restore records")

    monkeypatch.setattr(
        "edison.core.session.lifecycle.recovery.restore_records_to_global_transactional",
        _boom_restore,
    )

    import edison.core.session.persistence.repository as sess_repo_mod

    def _boom_transition(*_args, **_kwargs):
        raise AssertionError("verify_session_health must not transition session state")

    monkeypatch.setattr(sess_repo_mod.SessionRepository, "transition", _boom_transition, raising=True)

    health = verify_session_health("python-pid-1")
    assert health["ok"] is True
