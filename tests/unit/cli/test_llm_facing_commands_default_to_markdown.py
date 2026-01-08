"""Regression tests: LLM-facing CLI commands must NOT default to JSON.

These commands are consumed by LLM agents and should default to markdown
for better readability. JSON should only be output when explicitly requested
via --json or --format json.

Policy:
- session/context.py: default format = markdown
- task/status.py: default format = markdown
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tests.helpers.session import ensure_session
from tests.helpers.task import ensure_task


@pytest.mark.session
def test_session_context_default_format_is_not_json(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Session context command must default to markdown, not JSON."""
    session_id = "sess-context-default-fmt-001"
    ensure_session(session_id, state="active")

    from edison.cli.session.context import main as context_main

    # No --json, no --format: should default to markdown
    args = argparse.Namespace(
        session_id=session_id,
        json=False,
        format="markdown",  # Expected after using add_format_flag
        repo_root=isolated_project_env,
    )
    rc = context_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Output should NOT be valid JSON (it should be markdown)
    try:
        json.loads(out)
        pytest.fail("Output was JSON when it should be markdown by default")
    except json.JSONDecodeError:
        pass  # Expected: not JSON

    # Output should contain markdown markers
    assert "## Edison Context" in out or "**" in out or "#" in out


@pytest.mark.session
def test_session_context_json_flag_outputs_json(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Session context command should output JSON when --json is specified."""
    session_id = "sess-context-json-flag-001"
    ensure_session(session_id, state="active")

    from edison.cli.session.context import main as context_main

    args = argparse.Namespace(
        session_id=session_id,
        json=True,
        format="json",  # --json should override to json
        repo_root=isolated_project_env,
    )
    rc = context_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Output should be valid JSON
    data = json.loads(out)
    assert isinstance(data, dict)


@pytest.mark.session
def test_session_context_has_format_argument() -> None:
    """Session context command should accept --format argument."""
    from edison.cli.session.context import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)

    # Should be able to parse --format markdown
    args = parser.parse_args(["--format", "markdown"])
    assert args.format == "markdown"

    # Should be able to parse --format json
    args = parser.parse_args(["--format", "json"])
    assert args.format == "json"

    # Default should be markdown
    args = parser.parse_args([])
    assert args.format == "markdown"


@pytest.mark.session
def test_task_status_default_format_is_not_json(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Task status command must default to markdown, not JSON."""
    task_id = "001-test-format-default"
    ensure_task(task_id, state="todo", project_root=isolated_project_env)

    from edison.cli.task.status import main as status_main

    # No --json, no --format: should default to markdown/text (not JSON)
    args = argparse.Namespace(
        record_id=task_id,
        status=None,
        reason=None,
        type="task",
        dry_run=False,
        force=False,
        session=None,
        json=False,
        format="markdown",  # Expected after using add_format_flag
        repo_root=isolated_project_env,
    )
    rc = status_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Output should NOT be valid JSON (it should be text/markdown)
    try:
        json.loads(out)
        pytest.fail("Output was JSON when it should be markdown by default")
    except json.JSONDecodeError:
        pass  # Expected: not JSON

    # Output should contain text markers
    assert "Task:" in out or "Status:" in out


@pytest.mark.session
def test_task_status_json_flag_outputs_json(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Task status command should output JSON when --json is specified."""
    task_id = "002-test-json-output"
    ensure_task(task_id, state="todo", project_root=isolated_project_env)

    from edison.cli.task.status import main as status_main

    args = argparse.Namespace(
        record_id=task_id,
        status=None,
        reason=None,
        type="task",
        dry_run=False,
        force=False,
        session=None,
        json=True,
        format="json",
        repo_root=isolated_project_env,
    )
    rc = status_main(args)
    assert rc == 0

    out = capsys.readouterr().out

    # Output should be valid JSON
    data = json.loads(out)
    assert isinstance(data, dict)
    assert "record_id" in data


@pytest.mark.session
def test_task_status_has_format_argument() -> None:
    """Task status command should accept --format argument."""
    from edison.cli.task.status import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)

    # Should be able to parse --format markdown
    args = parser.parse_args(["test-id", "--format", "markdown"])
    assert args.format == "markdown"

    # Should be able to parse --format json
    args = parser.parse_args(["test-id", "--format", "json"])
    assert args.format == "json"

    # Default should be markdown
    args = parser.parse_args(["test-id"])
    assert args.format == "markdown"
