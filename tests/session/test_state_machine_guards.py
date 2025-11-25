"""Session/task state machine guard tests (Phase 1B).

These tests focus on the pure guard logic exposed by the RulesEngine
for common task transitions. They do not invoke CLI scripts and rely
only on in-memory task/session dictionaries.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from edison.core.rules import RulesEngine 
def _engine() -> RulesEngine:
    # Minimal rules config; context rules are not required for guard checks.
    return RulesEngine({"rules": {"enforcement": False}})


def test_guard_todo_to_wip_requires_matching_session_id() -> None:
    engine = _engine()
    task: Dict[str, Any] = {"id": "T-1", "session_id": "sess-123"}
    session: Dict[str, Any] = {"id": "sess-999"}

    allowed, msg = engine.check_transition_guards("todo", "wip", task, session)

    assert allowed is False
    assert msg
    assert "Task not claimed by this session" in msg


def test_guard_todo_to_wip_allows_when_session_matches() -> None:
    engine = _engine()
    task: Dict[str, Any] = {"id": "T-2", "session_id": "sess-123"}
    session: Dict[str, Any] = {"id": "sess-123"}

    allowed, msg = engine.check_transition_guards("todo", "wip", task, session)

    assert allowed is True
    assert msg is None


def test_guard_wip_to_done_requires_implementation_report(tmp_path, monkeypatch) -> None:
    """wip → done must see an implementation-report.json in evidence tree."""
    # Arrange: point project root at tmp_path and create evidence tree
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    task_id = "T-impl"
    ev_root = (
        Path(tmp_path)
        / ".project"
        / "qa"
        / "validation-evidence"
        / task_id
        / "round-1"
    )
    ev_root.mkdir(parents=True, exist_ok=True)

    engine = _engine()
    task: Dict[str, Any] = {"id": task_id}

    # Initially, no implementation-report.json → guard must fail
    allowed, msg = engine.check_transition_guards("wip", "done", task, {})
    assert allowed is False
    assert msg

    # Write minimal implementation report and expect guard to pass
    (ev_root / "implementation-report.json").write_text("{}", encoding="utf-8")
    allowed_ok, msg_ok = engine.check_transition_guards("wip", "done", task, {})
    assert allowed_ok is True
    assert msg_ok is None


def test_guard_done_to_validated_requires_blocking_validators_passed() -> None:
    engine = _engine()
    task: Dict[str, Any] = {"id": "T-val"}
    session: Dict[str, Any] = {}

    validation_results = {
        "blocking_validators": [
            {"name": "security", "passed": False},
            {"name": "performance", "passed": True},
        ]
    }

    allowed, msg = engine.check_transition_guards(
        "done", "validated", task, session, validation_results
    )
    assert allowed is False
    assert msg
    assert "security" in msg

    validation_results_ok = {
        "blocking_validators": [
            {"name": "security", "passed": True},
            {"name": "performance", "passed": True},
        ]
    }
    allowed_ok, msg_ok = engine.check_transition_guards(
        "done", "validated", task, session, validation_results_ok
    )
    assert allowed_ok is True
    assert msg_ok is None


def test_guard_done_to_wip_requires_rollback_reason() -> None:
    engine = _engine()
    task: Dict[str, Any] = {"id": "T-rollback"}

    # Missing reason → guard blocks
    allowed, msg = engine.check_transition_guards("done", "wip", task, {})
    assert allowed is False
    assert msg
    assert "rollback" in msg.lower()

    # With explicit rollbackReason → allowed
    task_with_reason = {"id": "T-rollback", "rollbackReason": "found regression"}
    allowed_ok, msg_ok = engine.check_transition_guards(
        "done", "wip", task_with_reason, {}
    )
    assert allowed_ok is True
    assert msg_ok is None

