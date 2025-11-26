"""
Tests for CLI error handling and structured output.

This module tests error handling functions extracted from the original cli.py god file.

Following STRICT TDD: These tests are written FIRST (RED phase) before
the implementation exists.

Note: Some tests are adapted from test_cli_utils_run_cli.py
"""

from __future__ import annotations

import json
from typing import Any, Optional

import pytest


def test_json_output_success_schema() -> None:
    """json_output should produce correct success schema."""
    from edison.core.utils.cli.errors import json_output

    result = json_output(success=True, data={"result": "ok"})
    parsed = json.loads(result)

    assert parsed["success"] is True
    assert parsed["data"] == {"result": "ok"}
    assert parsed["error"] == {"message": "", "code": "", "context": {}}


def test_json_output_error_dict_schema() -> None:
    """json_output should handle error as dict."""
    from edison.core.utils.cli.errors import json_output

    error_data = {
        "message": "Something failed",
        "code": "ERR_FAIL",
        "context": {"detail": "info"}
    }
    result = json_output(success=False, data={}, error=error_data)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["message"] == "Something failed"
    assert parsed["error"]["code"] == "ERR_FAIL"
    assert parsed["error"]["context"] == {"detail": "info"}


def test_json_output_error_string() -> None:
    """json_output should handle error as string."""
    from edison.core.utils.cli.errors import json_output

    result = json_output(success=False, data={}, error="Error message")
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["message"] == "Error message"
    assert parsed["error"]["code"] == ""
    assert parsed["error"]["context"] == {}


def test_json_output_no_error() -> None:
    """json_output should handle None error."""
    from edison.core.utils.cli.errors import json_output

    result = json_output(success=True, data={"key": "value"}, error=None)
    parsed = json.loads(result)

    assert parsed["success"] is True
    assert parsed["data"] == {"key": "value"}
    assert parsed["error"]["message"] == ""


def test_cli_error_json_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """cli_error should emit structured JSON in json_mode."""
    from edison.core.utils.cli.errors import cli_error

    exit_code = cli_error(
        "Test error",
        code="TEST_ERR",
        json_mode=True,
        context={"foo": "bar"}
    )

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)

    assert exit_code == 1
    assert parsed["success"] is False
    assert parsed["error"]["message"] == "Test error"
    assert parsed["error"]["code"] == "TEST_ERR"
    assert parsed["error"]["context"]["foo"] == "bar"


def test_cli_error_text_mode() -> None:
    """cli_error should emit text message in text mode."""
    from io import StringIO
    from edison.core.utils.cli.errors import cli_error

    # Provide custom stream
    stream = StringIO()
    exit_code = cli_error("Test error", code="TEST_ERR", json_mode=False, stream=stream)

    output = stream.getvalue()

    assert exit_code == 1
    assert "TEST_ERR" in output
    assert "Test error" in output


def test_cli_error_default_code() -> None:
    """cli_error should use default ERROR code."""
    from edison.core.utils.cli.errors import cli_error

    exit_code = cli_error("Test", json_mode=True)

    assert exit_code == 1


def test_run_cli_success_passthrough(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli should pass through successful output and return code 0."""
    from edison.core.utils.cli.errors import run_cli

    def main_ok() -> int:
        print("ok-main")
        return 0

    code = run_cli(main_ok, json_errors=True)
    captured = capsys.readouterr()

    assert code == 0
    assert "ok-main" in captured.out


def test_run_cli_none_return_is_success(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli should treat None return as success (code 0)."""
    from edison.core.utils.cli.errors import run_cli

    def main_none() -> None:
        print("done")

    code = run_cli(main_none, json_errors=True)
    captured = capsys.readouterr()

    assert code == 0
    assert "done" in captured.out


def test_run_cli_edison_error_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """EdisonError subclasses should be rendered via json_output()."""
    from edison.core import exceptions
    from edison.core.utils.cli.errors import run_cli

    def main_fail() -> None:
        raise exceptions.TaskNotFoundError("missing task", context={"taskId": "T-1"})

    code = run_cli(main_fail, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("message") == "missing task"
    assert err.get("code") == "TaskNotFoundError"
    assert err.get("context", {}).get("taskId") == "T-1"


def test_run_cli_edison_error_text_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """EdisonError should be rendered as text when json_errors=False."""
    from edison.core import exceptions
    from edison.core.utils.cli.errors import run_cli

    def main_fail() -> None:
        raise exceptions.TaskNotFoundError("missing task")

    code = run_cli(main_fail, json_errors=False)
    captured = capsys.readouterr()

    assert code != 0
    assert "TaskNotFoundError" in captured.err
    assert "missing task" in captured.err


def test_run_cli_keyboard_interrupt_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """KeyboardInterrupt should be mapped to CANCELLED json error."""
    from edison.core.utils.cli.errors import run_cli

    def main_interrupt() -> None:
        raise KeyboardInterrupt()

    code = run_cli(main_interrupt, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("code") == "CANCELLED"
    assert "cancelled" in (err.get("message") or "").lower()


def test_run_cli_keyboard_interrupt_text_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """KeyboardInterrupt should emit text in text mode."""
    from edison.core.utils.cli.errors import run_cli

    def main_interrupt() -> None:
        raise KeyboardInterrupt()

    code = run_cli(main_interrupt, json_errors=False)
    captured = capsys.readouterr()

    assert code != 0
    assert "cancelled" in captured.err.lower()


def test_run_cli_unexpected_exception_to_json(capsys: pytest.CaptureFixture[str]) -> None:
    """Non-Edison exceptions should emit INTERNAL_ERROR with type context."""
    from edison.core.utils.cli.errors import run_cli

    class CustomError(RuntimeError):
        pass

    def main_boom() -> None:
        raise CustomError("boom")

    code = run_cli(main_boom, json_errors=True)
    captured = capsys.readouterr()

    assert code != 0
    obj = json.loads(captured.out or "{}")
    assert obj.get("success") is False
    err = obj.get("error") or {}
    assert err.get("code") == "INTERNAL_ERROR"
    assert "boom" in (err.get("message") or "")
    ctx = err.get("context") or {}
    assert ctx.get("type") == "CustomError"


def test_run_cli_unexpected_exception_text_mode(capsys: pytest.CaptureFixture[str]) -> None:
    """Unexpected exceptions should emit text in text mode."""
    from edison.core.utils.cli.errors import run_cli

    def main_boom() -> None:
        raise RuntimeError("boom")

    code = run_cli(main_boom, json_errors=False)
    captured = capsys.readouterr()

    assert code != 0
    assert "boom" in captured.err


def test_run_cli_forwards_args_kwargs(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli should forward args and kwargs to main function."""
    from edison.core.utils.cli.errors import run_cli

    def main_with_args(name: str, count: int = 1) -> int:
        print(f"{name}: {count}")
        return 0

    code = run_cli(main_with_args, "test", count=3, json_errors=False)
    captured = capsys.readouterr()

    assert code == 0
    assert "test: 3" in captured.out
