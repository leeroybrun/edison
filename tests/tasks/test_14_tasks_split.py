"""Tests for task splitting functionality."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers.test_env import TestProjectDir
from helpers.command_runner import run_script, assert_command_success, assert_json_output


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.session
@pytest.mark.task
def test_tasks_split_creates_children_and_qas(test_project_dir: TestProjectDir):
    session_id = "split-session"
    # Create session
    res = run_script("session", ["new", "--owner", session_id, "--session-id", session_id, "--mode", "start"], cwd=test_project_dir.tmp_path)
    assert_command_success(res)

    # Create parent task in session
    parent_num, wave, parent_slug = "900", "wave1", "feature-parent"
    parent_id = f"{parent_num}-{wave}-{parent_slug}"
    res_new = run_script("tasks/new", ["--id", parent_num, "--wave", wave, "--slug", parent_slug, "--session", session_id], cwd=test_project_dir.tmp_path)
    assert_command_success(res_new)

    # Split into two children
    res_split = run_script(
        "tasks/split",
        [
            "--parent", parent_id,
            "--session", session_id,
            "--owners", "alice,bob",
            "--slugs", "ui,api",
        ],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(res_split)
    payload = json.loads(res_split.stdout)
    assert payload["parent"] == parent_id
    assert payload["session"] == session_id
    assert payload["count"] == 2
    ids = [c["id"] for c in payload["children"]]
    assert f"{parent_num}.1-{wave}-ui" in ids
    assert f"{parent_num}.2-{wave}-api" in ids

    # Verify files exist under session tree
    for cid in ids:
        task_path = test_project_dir.project_root / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{cid}.md"
        assert task_path.exists(), f"missing child task: {task_path}"
        qa_path = test_project_dir.project_root / "sessions" / "wip" / session_id / "qa" / "waiting" / f"{cid}-qa.md"
        assert qa_path.exists(), f"missing child QA: {qa_path}"

    # Verify links recorded in session JSON
    sess_path = test_project_dir.project_root / "sessions" / "wip" / f"{session_id}.json"
    data = json.loads(sess_path.read_text())
    assert set(data["tasks"][parent_id]["childIds"]) == set(ids)
    for cid in ids:
        assert data["tasks"][cid]["parentId"] == parent_id
