"""Test 01: Session Management

Tests for session creation, lifecycle, and state transitions using REAL CLIs.

Test Coverage:
- Session creation via real `session new` CLI
- Session state transitions using real `session` CLI
- Session metadata management
- Session ownership and tracking
- Session completion via real `session complete` CLI

IMPORTANT: These tests execute REAL CLI commands, NOT mock data.
All behaviors must match the composed guidelines in `.edison/_generated/guidelines/orchestrators/SESSION_WORKFLOW.md`.
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from helpers import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_json_output,
    assert_output_contains,
)
from helpers.assertions import (
    assert_file_exists,
    assert_file_contains,
)


@pytest.mark.session
@pytest.mark.fast
def test_create_basic_session(project_dir: TestProjectDir):
    """✅ CORRECT: Create session using REAL session new CLI."""
    session_id = "sess-session-mgmt-basic"

    # Execute REAL session new CLI
    result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )

    # Validate command succeeded
    assert_command_success(result)

    # Validate session file was created in .project/sessions/wip/ (NOT .agents/sessions/)
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_path)

    # Validate session JSON has required fields (REAL structure from CLI)
    session_data = json.loads(session_path.read_text())

    # Real session structure uses nested "meta" object
    assert "meta" in session_data, "Session should have meta object"
    assert session_data["meta"]["sessionId"] == session_id, "sessionId should match"
    assert session_data["meta"]["status"] == "active", "New sessions start in active status"
    assert "createdAt" in session_data["meta"], "Session should have createdAt timestamp"

    # Real session structure uses objects, NOT arrays for tasks/qa
    assert "tasks" in session_data, "Session should have tasks object"
    assert "qa" in session_data, "Session should have qa object"
    assert isinstance(session_data["tasks"], dict), "tasks should be a dict (object)"
    assert isinstance(session_data["qa"], dict), "qa should be a dict (object)"

    # Real sessions have git metadata and activityLog
    assert "git" in session_data, "Session should have git metadata"
    assert "activityLog" in session_data, "Session should have activity log"


@pytest.mark.session
@pytest.mark.worktree
@pytest.mark.fast
def test_create_worktree_session(project_dir: TestProjectDir):
    """✅ CORRECT: Create session with worktree via REAL session new CLI.

    NOTE: Real session CLI automatically creates worktrees by default.
    This test validates the git metadata structure in the session JSON.
    """
    session_id = "sess-session-mgmt-worktree"

    # Execute REAL session new CLI (creates worktree by default per guidelines)
    result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )

    # Validate command succeeded
    assert_command_success(result)

    # Validate session file exists
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_path)

    # Verify session has git metadata (REAL CLI creates worktrees automatically)
    session_data = json.loads(session_path.read_text())
    assert "git" in session_data, "Session should have git metadata"

    # Real behavior: In test environment without git repo, git fields may be None
    # In real production environment with git, worktree would be created
    # This test validates the structure exists, not the specific values
    assert "worktreePath" in session_data["git"], "Git metadata should include worktreePath"
    assert "branchName" in session_data["git"], "Git metadata should include branchName"
    assert "baseBranch" in session_data["git"], "Git metadata should include baseBranch"

    # Note: In non-git test environment, these may be None
    # In production git environment, they would be:
    # - branchName: f"session/{session_id}"
    # - baseBranch: "main"


@pytest.mark.session
@pytest.mark.task
@pytest.mark.fast
def test_session_task_tracking(project_dir: TestProjectDir):
    """✅ CORRECT: Sessions track tasks via REAL tasks/claim CLI.

    Per SESSION_WORKFLOW.md: Tasks are registered in sessions via tasks/claim --session.
    """
    session_id = "sess-session-mgmt-tasks"
    task_num = "100"
    wave = "wave1"
    slug = "test-task"
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
        ["--id", task_num, "--wave", wave, "--slug", slug, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(task_result)

    # Claim task into session via REAL CLI (this registers it in session.tasks)
    claim_result = run_script(
        "tasks/claim",
        [task_id, "--status", "wip", "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(claim_result)

    # Session JSON is not a task index; directory structure is the source of truth.
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_path)

    # Verify session-scoped task file has Owner field set (claimed under session → tasks/wip)
    task_path = (
        project_dir.project_root
        / "sessions" / "wip" / session_id / "tasks" / "wip" / f"{task_id}.md"
    )
    assert_file_exists(task_path)
    from helpers.assertions import read_file
    task_content = read_file(task_path)
    from edison.core.utils.text import parse_frontmatter
    fm = parse_frontmatter(task_content).frontmatter
    assert fm.get("owner"), "Task should have owner frontmatter"


@pytest.mark.session
@pytest.mark.fast
def test_session_status_command(project_dir: TestProjectDir):
    """✅ CORRECT: Test session status CLI shows session info.

    Per SESSION_WORKFLOW.md: Use `session status <session-id>` to inspect sessions.
    """
    session_id = "sess-session-mgmt-status"

    # Create session via REAL CLI
    create_result = run_script(
        "session",
        ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(create_result)

    # Execute REAL session status CLI
    status_result = run_script(
        "session",
        ["status", session_id],
        cwd=project_dir.tmp_path,
    )

    # Validate command succeeded
    assert_command_success(status_result)

    # Validate output contains session information
    assert_output_contains(status_result, session_id)
    assert_output_contains(status_result, "active")


@pytest.mark.session
@pytest.mark.fast
def test_multiple_sessions(project_dir: TestProjectDir):
    """✅ CORRECT: Create multiple concurrent sessions via REAL CLI."""
    sessions = ["sess-session-mgmt-1", "sess-session-mgmt-2", "sess-session-mgmt-3"]

    # Create multiple sessions via REAL CLI
    for session_id in sessions:
        result = run_script(
            "session",
            ["new", "--owner", "test", "--session-id", session_id, "--mode", "start"],
            cwd=project_dir.tmp_path,
        )
        assert_command_success(result)

    # Verify all exist in .project/sessions/wip/
    for session_id in sessions:
        session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
        assert_file_exists(session_path)

    # Each should have unique session ID in meta
    session_ids = set()
    for session_id in sessions:
        session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
        data = json.loads(session_path.read_text())
        session_ids.add(data["meta"]["sessionId"])

    assert len(session_ids) == len(sessions), "Session IDs should be unique"


@pytest.mark.session
@pytest.mark.qa
@pytest.mark.fast
def test_session_qa_tracking(project_dir: TestProjectDir):
    """✅ CORRECT: Sessions track QA via REAL qa/new CLI.

    Per SESSION_WORKFLOW.md: QA files created via `qa/new <task-id> --session <session-id>`.
    """
    session_id = "sess-session-mgmt-qa"
    task_num = "150"
    wave = "wave1"
    slug = "qa-task"
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

    # Create QA via REAL CLI (registers in session automatically)
    qa_result = run_script(
        "qa/new",
        [task_id, "--session", session_id],
        cwd=project_dir.tmp_path,
    )
    assert_command_success(qa_result)

    # Verify QA file was created in qa/waiting/ (per SESSION_WORKFLOW.md)
    qa_path = project_dir.project_root / "qa" / "waiting" / f"{task_id}-qa.md"
    assert_file_exists(qa_path)

    # Session JSON is not a QA index; directory structure is the source of truth.
    session_path = project_dir.project_root / "sessions" / "wip" / session_id / "session.json"
    assert_file_exists(session_path)
