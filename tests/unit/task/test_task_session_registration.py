"""Test that tasks and QA are properly registered in session.json.

This test verifies the fix for the session tracking issue where tasks/QA
were being created but not registered in the session's tasks/qa dictionaries.
"""
import json
import pytest
from pathlib import Path

from edison.core.task.workflow import TaskQAWorkflow
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.core.models import Session


def test_create_task_registers_in_session(isolated_project_env):
    """When creating a task with session_id, it should register in session.json."""
    project_root = isolated_project_env
    session_id = "test-session-001"
    task_id = "T-001"

    # Create session first
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create task with session
    workflow = TaskQAWorkflow(project_root)
    task = workflow.create_task(
        task_id=task_id,
        title="Test Task",
        description="Test description",
        session_id=session_id,
        owner="test-user",
        create_qa=True,
    )

    # Reload session and verify task is registered
    session = session_repo.get(session_id)
    assert session is not None
    assert task_id in session.tasks, f"Task {task_id} should be registered in session.tasks"

    # Verify task entry has correct data
    task_entry = session.tasks[task_id]
    assert task_entry.record_id == task_id
    assert task_entry.owner == "test-user"
    assert task_entry.status == "todo"


def test_create_task_registers_qa_in_session(isolated_project_env):
    """When creating a task with QA, the QA should also be registered."""
    project_root = isolated_project_env
    session_id = "test-session-002"
    task_id = "T-002"
    qa_id = f"{task_id}-qa"

    # Create session first
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create task with QA
    workflow = TaskQAWorkflow(project_root)
    task = workflow.create_task(
        task_id=task_id,
        title="Test Task",
        session_id=session_id,
        owner="test-user",
        create_qa=True,
    )

    # Reload session and verify QA is registered
    session = session_repo.get(session_id)
    assert session is not None
    assert qa_id in session.qa_records, f"QA {qa_id} should be registered in session.qa_records"

    # Verify QA entry has correct data
    qa_entry = session.qa_records[qa_id]
    assert qa_entry.record_id == qa_id
    assert qa_entry.task_id == task_id
    assert qa_entry.status == "waiting"


def test_claim_task_registers_in_session(isolated_project_env):
    """When claiming a task into a session, it should register in session.json."""
    project_root = isolated_project_env
    session_id = "test-session-003"
    task_id = "T-003"

    # Create session
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create task WITHOUT session (global task)
    workflow = TaskQAWorkflow(project_root)
    workflow.create_task(
        task_id=task_id,
        title="Test Task",
        session_id=None,  # Global task
        create_qa=True,
    )

    # Claim task into session
    task = workflow.claim_task(task_id, session_id)

    # Reload session and verify task is registered
    session = session_repo.get(session_id)
    assert session is not None
    assert task_id in session.tasks, f"Task {task_id} should be registered when claimed"

    # Verify task entry shows wip status
    task_entry = session.tasks[task_id]
    assert task_entry.status == "wip"


def test_complete_task_updates_session(isolated_project_env):
    """When completing a task, session.json should be updated."""
    project_root = isolated_project_env
    session_id = "test-session-004"
    task_id = "T-004"

    # Create session
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create and claim task
    workflow = TaskQAWorkflow(project_root)
    workflow.create_task(
        task_id=task_id,
        title="Test Task",
        session_id=session_id,
        create_qa=True,
    )
    workflow.claim_task(task_id, session_id)

    # Complete task
    task = workflow.complete_task(task_id, session_id)

    # Reload session and verify task status updated
    session = session_repo.get(session_id)
    assert session is not None
    assert task_id in session.tasks

    # Verify task entry shows done status
    task_entry = session.tasks[task_id]
    assert task_entry.status == "done"


def test_complete_task_updates_qa_in_session(isolated_project_env):
    """When completing a task, QA status should update in session.json."""
    project_root = isolated_project_env
    session_id = "test-session-005"
    task_id = "T-005"
    qa_id = f"{task_id}-qa"

    # Create session
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create, claim, and complete task
    workflow = TaskQAWorkflow(project_root)
    workflow.create_task(
        task_id=task_id,
        title="Test Task",
        session_id=session_id,
        create_qa=True,
    )
    workflow.claim_task(task_id, session_id)
    workflow.complete_task(task_id, session_id)

    # Reload session and verify QA status updated
    session = session_repo.get(session_id)
    assert session is not None
    assert qa_id in session.qa_records

    # Verify QA entry shows todo status (advanced from waiting)
    qa_entry = session.qa_records[qa_id]
    assert qa_entry.status == "todo"


def test_session_json_file_contains_registrations(isolated_project_env):
    """Verify session.json file on disk contains task/QA registrations."""
    project_root = isolated_project_env
    session_id = "test-session-006"
    task_id = "T-006"
    qa_id = f"{task_id}-qa"

    # Create session
    session_repo = SessionRepository(project_root)
    session = Session.create(session_id, state="wip")
    session_repo.create(session)

    # Create task
    workflow = TaskQAWorkflow(project_root)
    workflow.create_task(
        task_id=task_id,
        title="Test Task",
        session_id=session_id,
        create_qa=True,
    )

    # Read session.json directly from disk
    session_path = project_root / ".project" / "sessions" / "wip" / session_id / "session.json"
    assert session_path.exists(), "Session JSON file should exist"

    with open(session_path) as f:
        session_data = json.load(f)

    # Verify structure
    assert "tasks" in session_data
    assert "qa" in session_data
    assert isinstance(session_data["tasks"], dict)
    assert isinstance(session_data["qa"], dict)

    # Verify registrations
    assert task_id in session_data["tasks"], f"Task {task_id} should be in session.json tasks"
    assert qa_id in session_data["qa"], f"QA {qa_id} should be in session.json qa"


def test_create_task_without_session_does_not_register(isolated_project_env):
    """Creating a global task (no session) should not modify any session."""
    project_root = isolated_project_env
    task_id = "T-007"

    # Create global task
    workflow = TaskQAWorkflow(project_root)
    workflow.create_task(
        task_id=task_id,
        title="Global Task",
        session_id=None,  # No session
        create_qa=True,
    )

    # No session.json files should be created/modified
    sessions_dir = project_root / ".project" / "sessions"
    if sessions_dir.exists():
        for state_dir in ["wip", "done", "validated"]:
            state_path = sessions_dir / state_dir
            if state_path.exists():
                # Count session files
                session_files = list(state_path.glob("*.json"))
                # If any exist, verify they don't contain our task
                for session_file in session_files:
                    with open(session_file) as f:
                        session_data = json.load(f)
                    if "tasks" in session_data:
                        assert task_id not in session_data["tasks"], \
                            f"Global task should not appear in {session_file}"
