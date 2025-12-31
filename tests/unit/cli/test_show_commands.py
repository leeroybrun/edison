from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from tests.helpers.fixtures import create_task_file, create_qa_file


def _parse_json_stdout(capsys: pytest.CaptureFixture[str]) -> dict:
    out = capsys.readouterr().out
    return json.loads(out)


def test_task_show_emits_json_with_path_and_content(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_id = "001-test-task-show"
    create_task_file(isolated_project_env, task_id, state="todo", title="Task show test")

    from edison.cli.task.show import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([task_id, "--json", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0

    payload = _parse_json_stdout(capsys)
    assert payload["recordType"] == "task"
    assert payload["id"] == task_id
    assert "path" in payload and payload["path"]
    assert payload["content"].lstrip().startswith("---")
    assert f"id: {task_id}" in payload["content"]


def test_qa_show_emits_json_with_path_and_content(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_id = "002-test-task-for-qa-show"
    qa_id = f"{task_id}-qa"
    create_task_file(isolated_project_env, task_id, state="todo", title="Task for QA show test")
    create_qa_file(isolated_project_env, qa_id, task_id=task_id, state="waiting", title="QA show test")

    from edison.cli.qa.show import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([qa_id, "--json", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0

    payload = _parse_json_stdout(capsys)
    assert payload["recordType"] == "qa"
    assert payload["id"] == qa_id
    assert payload["task_id"] == task_id
    assert "path" in payload and payload["path"]
    assert payload["content"].lstrip().startswith("---")
    assert f"id: {qa_id}" in payload["content"]


def test_session_show_emits_json_with_path_and_content(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=isolated_project_env)
    session_id = "sess-001-show"
    repo.create(Session.create(session_id, owner="test", state="active"))

    from edison.cli.session.show import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([session_id, "--json", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0

    payload = _parse_json_stdout(capsys)
    assert payload["recordType"] == "session"
    assert payload["id"] == session_id
    assert "path" in payload and payload["path"]
    assert isinstance(payload["session"], dict)
