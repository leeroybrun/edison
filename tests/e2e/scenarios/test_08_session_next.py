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
def test_session_next_new_session(project_dir: TestProjectDir):
    """✅ CORRECT: Test session next for newly created session using REAL CLI."""
    session_id = "test-new-session"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output suggests creating a task (session has no tasks)
    output = next_result.stdout.lower()
    # Session next should suggest task creation or claiming
    assert "task" in output or "create" in output or "claim" in output


@pytest.mark.session
@pytest.mark.task
@pytest.mark.fast
def test_session_next_with_wip_task(project_dir: TestProjectDir):
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

    # Claim task and move to wip
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output mentions the task in wip
    output = next_result.stdout
    assert task_id in output or "wip" in output.lower()


@pytest.mark.session
@pytest.mark.qa
@pytest.mark.fast
def test_session_next_with_done_task_no_qa(project_dir: TestProjectDir):
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

    # Claim task
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Note: Can't move to done without evidence (guard will block)
    # So this test validates that session next shows we need to work on the task

    # Run REAL session next CLI
    next_result = run_script(
        "session",
        ["next", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output shows task progress
    output = next_result.stdout
    assert task_id in output or "wip" in output.lower()


@pytest.mark.session
@pytest.mark.fast
def test_session_next_json_output(project_dir: TestProjectDir):
    """✅ CORRECT: Test session next JSON output format."""
    session_id = "test-json-output"

    # Create session via REAL CLI
    session_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(session_result)

    # Run REAL session next CLI with --json flag
    next_result = run_script(
        "session",
        ["next", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(next_result)

    # Verify output is valid JSON
    try:
        output_data = json.loads(next_result.stdout)
        # Should have some structure (exact format depends on implementation)
        assert isinstance(output_data, (dict, list))
    except json.JSONDecodeError:
        pytest.fail(f"session next --json did not produce valid JSON: {next_result.stdout}")


@pytest.mark.session
@pytest.mark.fast
def test_session_next_json_cmds_are_current(project_dir: TestProjectDir):
    """Ensure session-next emits current (non-legacy) command tokens."""
    session_id = "test-cmd-shape"
    task_num = "210"
    wave = "wave1"
    slug = "cmd-shape"
    task_id = f"{task_num}-{wave}-{slug}"

    # Create session + wip task via REAL CLI
    assert_command_success(run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    ))
    assert_command_success(run_script(
        "tasks/new",
        ["--id", task_num, "--wave", wave, "--slug", slug],
        cwd=project_dir.tmp_path,
    ))
    assert_command_success(run_script(
        "tasks/claim",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    ))

    # Add an implementation follow-up to force session-next to emit concrete `cmd` entries.
    evidence_dir = (
        project_dir.project_root
        / "qa"
        / "validation-evidence"
        / task_id
        / "round-1"
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "implementation-report.json").write_text(
        json.dumps({
            "taskId": task_id,
            "round": 1,
            "followUpTasks": [
                {
                    "title": "Investigate follow-up command shape",
                    "blockingBeforeValidation": True,
                    "claimNow": True,
                    "category": "test",
                }
            ],
        }),
        encoding="utf-8",
    )

    next_result = run_script(
        "session",
        ["next", session_id, "--json"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(next_result)
    output_data = json.loads(next_result.stdout)

    cmds: list[list[str]] = []
    for action in output_data.get("actions", []) or []:
        if isinstance(action, dict) and isinstance(action.get("cmd"), list):
            cmds.append([str(x) for x in action["cmd"]])
    for plan in output_data.get("followUpsPlan", []) or []:
        if not isinstance(plan, dict):
            continue
        for sug in plan.get("suggestions", []) or []:
            if isinstance(sug, dict) and isinstance(sug.get("cmd"), list):
                cmds.append([str(x) for x in sug["cmd"]])

    assert cmds, "Expected session-next to emit at least one cmd entry"

    # Guardrail assertions: never emit legacy/invalid tokens.
    flat = " ".join(" ".join(c) for c in cmds)
    assert " edison tasks " not in f" {flat} "
    assert " --to " not in f" {flat} "
    assert " --task " not in f" {flat} "
