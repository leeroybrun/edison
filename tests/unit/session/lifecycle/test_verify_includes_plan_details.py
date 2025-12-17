from __future__ import annotations

from contextlib import contextmanager


def test_verify_session_health_includes_reports_missing_details(isolated_project_env, monkeypatch):
    """When session next reports missing items, verify should surface them in details."""
    from edison.core.session.lifecycle.verify import verify_session_health
    from edison.core.task import TaskRepository
    from edison.core.session.lifecycle import verify as verify_mod

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
        return {
            "actions": [],
            "blockers": [],
            "reportsMissing": [
                {
                    "taskId": "t-1",
                    "type": "context7",
                    "packages": ["next"],
                    "suggested": ["Write context7-next.txt"],
                }
            ],
        }

    monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

    health = verify_session_health("python-pid-1")

    assert health["ok"] is False
    assert health["categories"]["blockersOrReportsMissing"] is True
    assert health["details"], "expected verify to include reportsMissing details"

