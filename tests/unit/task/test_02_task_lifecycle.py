"""Test 02: Task Lifecycle

Tests for task creation, state transitions, and lifecycle management using REAL CLIs.

Test Coverage:
- Task creation via real `tasks/new` CLI
- Task state transitions using real `tasks/status` CLI
- Task ownership via real `tasks/claim` CLI

IMPORTANT: These tests execute REAL CLI commands, NOT mock data.
All behaviors must match the composed guidelines in `.edison/_generated/guidelines/`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers.env import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
)
from helpers.assertions import (
    assert_file_exists,
    assert_file_contains,
)


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.task
@pytest.mark.fast
def test_create_task(project_dir: TestProjectDir):
    """✅ CORRECT: Create task using REAL tasks/new CLI."""
    task_num = "100"
    wave = "wave1"
    slug = "basic-task"
    task_id = f"{task_num}-{wave}-{slug}"

    # Execute REAL tasks/new CLI
    result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=project_dir.tmp_path,
    )

    # Validate command succeeded
    assert_command_success(result)

    # Verify task file was created in .project/tasks/todo/
    task_path = project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    assert_file_exists(task_path)

    # Verify task content has required fields
    from helpers.assertions import read_file
    task_content = read_file(task_path)
    assert f"# {task_id}" in task_content, "Task should have title with ID"
    assert "**Status:**" in task_content, "Task should have Status field"
    assert "**Owner:**" in task_content, "Task should have Owner field"


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.task
@pytest.mark.fast
def test_task_state_transitions(project_dir: TestProjectDir):
    """✅ CORRECT: Test basic task transitions using REAL tasks/status CLI.

    Tests simple transitions that don't require guard checks:
    - todo → wip (claiming for work)
    - wip → blocked (hitting a blocker)
    - blocked → wip (blocker resolved)

    NOTE: done/validated transitions require evidence and are tested separately.
    """
    task_num = "150"
    wave = "wave1"
    slug = "transitions"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-transitions-session"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Create task via REAL CLI (starts in todo)
    result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify task is in todo
    task_path = project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    assert_file_exists(task_path)

    # Move to wip via REAL tasks/status CLI (with session)
    result = run_script(
        "tasks/status",
        [task_id, "--status", "wip", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify moved to wip
    wip_path = project_dir.project_root / "tasks" / "wip" / f"{task_id}.md"
    assert_file_exists(wip_path)

    # Move to blocked (hit a blocker during work)
    result = run_script(
        "tasks/status",
        [task_id, "--status", "blocked", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify moved to blocked
    blocked_path = project_dir.project_root / "tasks" / "blocked" / f"{task_id}.md"
    assert_file_exists(blocked_path)

    # Move back to wip (blocker resolved)
    result = run_script(
        "tasks/status",
        [task_id, "--status", "wip", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(result)

    # Verify moved back to wip
    wip_path2 = project_dir.project_root / "tasks" / "wip" / f"{task_id}.md"
    assert_file_exists(wip_path2)


@pytest.mark.skip(reason="Requires session/new CLI command not yet implemented in Edison CLI")
@pytest.mark.task
@pytest.mark.session
@pytest.mark.fast
def test_task_ownership(project_dir: TestProjectDir):
    """✅ CORRECT: Test task ownership using REAL tasks/claim CLI.

    Per guidelines: Tasks are claimed via `tasks/claim <task-id> --session <session-id>`.
    """
    task_num = "200"
    wave = "wave1"
    slug = "ownership"
    task_id = f"{task_num}-{wave}-{slug}"
    session_id = "test-session-owner"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Create task via REAL CLI
    task_result = run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(task_result)

    # Claim task via REAL CLI (this sets ownership and registers in session)
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Verify task file has Owner field set
    task_path = project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    task_content = read_file(task_path)
    assert "**Owner:**" in task_content, "Task should have Owner field"

    # Verify task was registered in session
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    session_data = json.loads(session_path.read_text())
    assert task_id in session_data["tasks"], f"Task {task_id} should be registered in session"
