from __future__ import annotations

import json
from typing import Any, Optional

import pytest


def _call_run_cli(main, *args: Any, **kwargs: Any) -> int:
    """
    Helper to call cli_utils.run_cli without exiting the interpreter.

    The helper simply forwards to run_cli and returns the exit code so tests
    can assert on stdout/stderr and codes without invoking sys.exit().
    """
    from edison.core import cli_utils  # type: ignore[attr-defined]

    return cli_utils.run_cli(main, *args, **kwargs)  # type: ignore[attr-defined]


def test_run_cli_success_passthrough(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli should pass through successful output and return code 0."""

    def main_ok() -> int:
        print("ok-main")
        return 0

    code = _call_run_cli(main_ok, json_errors=True)
    captured = capsys.readouterr()

    assert code == 0
    assert "ok-main" in captured.out
    # No structured error emitted on success
    assert captured.err == ""


def test_run_cli_edison_error_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """EdisonError subclasses should be rendered via json_output()."""
    from edison.core import exceptions  # type: ignore[attr-defined]

    def main_fail() -> None:
        raise exceptions.TaskNotFoundError("missing task", context={"taskId": "T-1"})  # type: ignore[attr-defined]

    code = _call_run_cli(main_fail, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("message") == "missing task"
    assert err.get("code") == "TaskNotFoundError"
    assert err.get("context", {}).get("taskId") == "T-1"


def test_run_cli_keyboard_interrupt_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """KeyboardInterrupt should be mapped to CANCELLED json error."""

    def main_interrupt() -> None:
        raise KeyboardInterrupt()

    code = _call_run_cli(main_interrupt, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("code") == "CANCELLED"
    assert "cancelled" in (err.get("message") or "").lower()


def test_run_cli_unexpected_exception_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Non-Edison exceptions should emit INTERNAL_ERROR with type context."""

    class CustomError(RuntimeError):
        pass

    def main_boom() -> None:
        raise CustomError("boom")

    code = _call_run_cli(main_boom, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("code") == "INTERNAL_ERROR"
    assert "boom" in (err.get("message") or "")
    ctx = err.get("context") or {}
    # Type name should be surfaced for debugging
    assert ctx.get("type") == "CustomError"

