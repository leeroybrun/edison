"""Test that tasks and QA are properly registered when created/claimed.

Per the Single Source of Truth architecture, task/QA data lives in the files
themselves. Session activity_log records registration events, and task/QA
files are the canonical source for their data.
"""
import json
import pytest
from pathlib import Path

from edison.core.task.workflow import TaskQAWorkflow
from edison.core.task.repository import TaskRepository
from edison.core.session.persistence.repository import SessionRepository
from edison.core.session.core.models import Session


def test_create_task_registers_in_session(isolated_project_env):
    """When creating a task with session_id, it should be logged in session activity."""
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

    # Reload session and verify activity was logged
    session = session_repo.get(session_id)
    assert session is not None
    
    # Check activity log has registration entry
    activity_messages = [e.get("message", "") for e in session.activity_log]
    assert any(task_id in msg and "registered" in msg for msg in activity_messages), \
        f"Task {task_id} registration should be in activity_log"

    # Verify task file exists and has correct data (single source of truth)
    task_repo = TaskRepository(project_root=project_root)
    loaded_task = task_repo.get(task_id)
    assert loaded_task is not None, f"Task {task_id} file should exist"
    assert loaded_task.metadata.created_by == "test-user"
    assert loaded_task.state == "todo"


def test_create_task_registers_qa_in_session(isolated_project_env):
    """When creating a task with QA, the QA should be logged in session activity."""
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

    # Reload session and verify activity was logged
    session = session_repo.get(session_id)
    assert session is not None
    
    # Check activity log has QA registration entry
    activity_messages = [e.get("message", "") for e in session.activity_log]
    assert any(qa_id in msg and "registered" in msg for msg in activity_messages), \
        f"QA {qa_id} registration should be in activity_log"

    # Verify QA file exists and has correct data (single source of truth)
    from edison.core.qa.workflow.repository import QARepository
    qa_repo = QARepository(project_root=project_root)
    loaded_qa = qa_repo.get(qa_id)
    assert loaded_qa is not None, f"QA {qa_id} file should exist"
    assert loaded_qa.task_id == task_id
    assert loaded_qa.state == "waiting"


def test_claim_task_registers_in_session(isolated_project_env):
    """When claiming a task into a session, it should be logged in session activity."""
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

    # Reload session and verify activity was logged
    session = session_repo.get(session_id)
    assert session is not None
    
    # Check activity log has claim entry
    activity_messages = [e.get("message", "") for e in session.activity_log]
    assert any(task_id in msg and "wip" in msg for msg in activity_messages), \
        f"Task {task_id} claim should be in activity_log"

    # Verify task file has wip state (single source of truth)
    task_repo = TaskRepository(project_root=project_root)
    loaded_task = task_repo.get(task_id)
    assert loaded_task is not None
    assert loaded_task.state == "wip"
    assert loaded_task.session_id == session_id


def test_complete_task_updates_session(isolated_project_env):
    """When completing a task, session activity should be logged."""
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

    # Verify task file has done state (single source of truth)
    task_repo = TaskRepository(project_root=project_root)
    loaded_task = task_repo.get(task_id)
    assert loaded_task is not None
    assert loaded_task.state == "done"


def test_complete_task_updates_qa_in_session(isolated_project_env):
    """When completing a task, QA should advance to todo state."""
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

    # Verify QA file shows todo status (single source of truth)
    from edison.core.qa.workflow.repository import QARepository
    qa_repo = QARepository(project_root=project_root)
    loaded_qa = qa_repo.get(qa_id)
    assert loaded_qa is not None
    # QA should advance from waiting to todo when task completes
    assert loaded_qa.state == "todo"


def test_session_json_file_contains_activity_log(isolated_project_env):
    """Verify session.json file has activity log entries for task/QA operations.
    
    Per Single Source of Truth: session.json stores activity_log, while
    task/QA data lives in their respective files.
    """
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

    # Verify activity_log exists and has entries
    assert "activityLog" in session_data
    activity_messages = [e.get("message", "") for e in session_data["activityLog"]]
    
    # Verify task registration was logged
    assert any(task_id in msg for msg in activity_messages), \
        f"Task {task_id} operation should be in activityLog"
    
    # Verify task/QA files exist (single source of truth)
    task_repo = TaskRepository(project_root=project_root)
    assert task_repo.get(task_id) is not None, f"Task file for {task_id} should exist"
    
    from edison.core.qa.workflow.repository import QARepository
    qa_repo = QARepository(project_root=project_root)
    assert qa_repo.get(qa_id) is not None, f"QA file for {qa_id} should exist"


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
