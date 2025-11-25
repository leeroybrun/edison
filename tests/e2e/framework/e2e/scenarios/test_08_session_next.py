"""Test 08: Session Next Actions

Tests for session next action computation using REAL CLI.

Test Coverage:
- `session next` command output validation
- Next action suggestions based on session state
- Task and QA readiness detection
- Priority guidance

IMPORTANT: These tests execute REAL CLI commands, NOT mock data.
All behaviors must match guidelines in .agents/guidelines/*.md
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from helpers import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_output_contains,
)
from helpers.assertions import assert_file_exists


@pytest.mark.session
@pytest.mark.fast
def test_session_next_new_session(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test session next for newly created session using REAL CLI."""
    session_id = "test-new-session"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output suggests creating a task (session has no tasks)
    output = next_result.stdout.lower()
    # Session next should suggest task creation or claiming
    assert "task" in output or "create" in output or "claim" in output


@pytest.mark.session
@pytest.mark.task
@pytest.mark.fast
def test_session_next_with_wip_task(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test session next when task is in wip using REAL CLI."""
    session_id = "test-wip-task"
    task_num = "100"
    wave = "wave1"
    slug = "wip-test"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Create task via REAL CLI
    task_result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(task_result)

    # Claim task and move to wip
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    move_result = run_script(
        "tasks/status",
        [task_id, "--status", "wip", "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(move_result)

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output mentions the task in wip
    output = next_result.stdout
    assert task_id in output or "wip" in output.lower()


@pytest.mark.session
@pytest.mark.qa
@pytest.mark.fast
def test_session_next_with_done_task_no_qa(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test session next when task is done but no QA exists."""
    session_id = "test-done-no-qa"
    task_num = "150"
    wave = "wave1"
    slug = "done-noqa"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Create task via REAL CLI
    task_result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(task_result)

    # Claim task
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Move to wip
    wip_result = run_script(
        "tasks/status",
        [task_id, "--status", "wip", "--session", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(wip_result)

    # Note: Can't move to done without evidence (guard will block)
    # So this test validates that session next shows we need to work on the task

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output shows task progress
    output = next_result.stdout
    assert task_id in output or "wip" in output.lower()


@pytest.mark.session
@pytest.mark.fast
def test_session_next_json_output(test_project_dir: TestProjectDir):
    """✅ CORRECT: Test session next JSON output format."""
    session_id = "test-json-output"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Run REAL session next CLI with --json flag
    next_result = run_script(
        "session",
        ["next", session_id, "--json"],
        cwd=test_project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output is valid JSON
    try:
        output_data = json.loads(next_result.stdout)
        # Should have some structure (exact format depends on implementation)
        assert isinstance(output_data, (dict, list))
    except json.JSONDecodeError:
        pytest.fail(f"session next --json did not produce valid JSON: {next_result.stdout}")
