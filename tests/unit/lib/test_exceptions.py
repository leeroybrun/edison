from __future__ import annotations

from typing import Dict


def test_edison_error_to_json_error_basic() -> None:
    from edison.core import exceptions  # type: ignore

    err = exceptions.EdisonError("something went wrong")  # type: ignore[attr-defined]
    payload: Dict[str, object] = err.to_json_error()

    assert payload["message"] == "something went wrong"
    assert payload["code"] == "EdisonError"
    assert isinstance(payload["context"], dict)


def test_edison_error_to_json_error_with_context() -> None:
    from edison.core import exceptions  # type: ignore

    err = exceptions.ValidationError("invalid state")  # type: ignore[attr-defined]
    # Attach a context mapping dynamically (common pattern in callers).
    err.context = {"taskId": "task-123"}  # type: ignore[attr-defined]

    payload = err.to_json_error()
    assert payload["message"] == "invalid state"
    assert payload["code"] == "ValidationError"
    assert payload["context"] == {"taskId": "task-123"}


def test_session_and_task_exceptions_inherit_both_domains() -> None:
    from edison.core import exceptions  # type: ignore

    sess_err = exceptions.SessionStateError("bad session")  # type: ignore[attr-defined]
    not_found = exceptions.SessionNotFoundError("missing")  # type: ignore[attr-defined]
    task_state = exceptions.TaskStateError("bad task")  # type: ignore[attr-defined]
    task_not_found = exceptions.TaskNotFoundError("no task")  # type: ignore[attr-defined]

    # Domain base + builtin compatibility
    assert isinstance(sess_err, exceptions.EdisonError)
    assert isinstance(sess_err, ValueError)
    assert isinstance(not_found, exceptions.SessionStateError)
    assert isinstance(task_state, exceptions.EdisonError)
    assert isinstance(task_state, ValueError)
    assert isinstance(task_not_found, exceptions.EdisonError)

    # JSON payloads use class names as codes
    assert sess_err.to_json_error()["code"] == "SessionStateError"
    assert not_found.to_json_error()["code"] == "SessionNotFoundError"
    assert task_state.to_json_error()["code"] == "TaskStateError"
    assert task_not_found.to_json_error()["code"] == "TaskNotFoundError"


def test_worktree_error_behaves_like_runtime_and_edison() -> None:
    from edison.core import exceptions  # type: ignore

    err = exceptions.WorktreeError("wt failed")  # type: ignore[attr-defined]
    assert isinstance(err, exceptions.EdisonError)
    assert isinstance(err, RuntimeError)
    payload = err.to_json_error()
    assert payload["message"] == "wt failed"
    assert payload["code"] == "WorktreeError"
