"""Tests for TaskQAWorkflow methods.

These tests ensure that TaskQAWorkflow correctly implements high-level
workflow operations like claim_task and complete_task that orchestrate
state transitions and file movements across Task and QA domains.
"""
from __future__ import annotations
from helpers.io_utils import write_yaml

import pytest
import importlib
from pathlib import Path
from edison.core.task.workflow import TaskQAWorkflow
from edison.core.task.repository import TaskRepository
from edison.core.qa.repository import QARepository
from edison.core.entity import PersistenceError, EntityMetadata
from edison.core.task.models import Task
from edison.core.qa.models import QARecord
from edison.core.config import get_semantic_state

@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup a repository environment with configuration."""
    repo = tmp_path
    (repo / ".git").mkdir()
    config_dir = repo / ".edison" / "core" / "config"
    
    # 1. defaults.yaml (State Machine)
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                        "done": {"allowed_transitions": [{"to": "validated"}]},
                        "validated": {"allowed_transitions": []},
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "todo"}]},
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}]},
                        "done": {"allowed_transitions": [{"to": "validated"}]},
                        "validated": {"allowed_transitions": []},
                    }
                }
            },
            "semantics": {
                "task": {
                    "todo": "todo",
                    "wip": "wip",
                    "done": "done",
                    "validated": "validated",
                },
                "qa": {
                    "waiting": "waiting",
                    "todo": "todo",
                    "wip": "wip",
                    "done": "done",
                    "validated": "validated",
                },
            },
        },
    )

    # 2. tasks.yaml
    write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                },
            }
        },
    )

    # 3. workflow.yaml (For semantic states)
    write_yaml(
        config_dir / "workflow.yaml",
        {
            "version": "1.0",
            "validationLifecycle": {
                "onApprove": {
                    "taskState": "done → validated",
                    "qaState": "done → validated"
                },
                "onReject": {
                    "taskState": "validated → wip",
                    "qaState": "wip → waiting"
                },
                "onRevalidate": {
                    "qaState": "waiting → todo"
                }
            },
            "timeouts": {
                "validation": "24h"
            }
        }
    )

    # 4. state-machine.yaml (redundant but good for completeness if config loads it)
    write_yaml(
        config_dir / "state-machine.yaml",
        {
            "statemachine": {
                "task": {"states": ["todo", "wip", "done"]},
                "qa": {"states": ["waiting", "todo", "wip", "done"]}
            }
        }
    )

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    import edison.core.utils.paths.resolver as resolver
    resolver._PROJECT_ROOT_CACHE = None
    
    # Clear config caches
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Reload config-dependent modules
    import edison.core.config.domains.task as task_config
    importlib.reload(task_config)
    import edison.core.task.paths as paths
    importlib.reload(paths)
    import edison.core.config.domains.workflow as wf
    importlib.reload(wf)

    return repo

def create_task_file(repo_path, task_id, state="todo", session_id=None):
    """Helper to create a task file."""
    repo = TaskRepository(project_root=repo_path)
    task = Task(
        id=task_id,
        state=state,
        title=f"Task {task_id}",
        session_id=session_id,
        metadata=EntityMetadata.create(created_by="test", session_id=session_id)
    )
    repo.save(task)
    return task

def create_qa_file(repo_path, qa_id, task_id, state="waiting", session_id=None):
    """Helper to create a QA file."""
    repo = QARepository(project_root=repo_path)
    qa = QARecord(
        id=qa_id,
        task_id=task_id,
        state=state,
        title=f"QA {task_id}",
        session_id=session_id,
        metadata=EntityMetadata.create(created_by="test", session_id=session_id)
    )
    repo.save(qa)
    return qa

def test_claim_task_moves_from_todo_to_wip(repo_env):
    """Test claiming a task moves it to session wip."""
    task_id = "T-1"
    session_id = "sess-1"

    # Create task in global todo
    todo_state = get_semantic_state("task", "todo")
    create_task_file(repo_env, task_id, state=todo_state)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    updated_task = workflow.claim_task(task_id, session_id)

    # Assert
    wip_state = get_semantic_state("task", "wip")
    assert updated_task.state == wip_state
    assert updated_task.session_id == session_id

    # Verify state history records the transition
    assert len(updated_task.state_history) > 0, "Should have state history"
    last_transition = updated_task.state_history[-1]
    assert last_transition.to_state == wip_state
    assert last_transition.reason == "claimed"

    # Verify file location
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "tasks" / wip_state / f"{task_id}.md"
    assert expected_path.exists()

    # Verify old file gone
    old_path = repo_env / ".project" / "tasks" / todo_state / f"{task_id}.md"
    assert not old_path.exists()

def test_claim_task_moves_qa_to_session(repo_env):
    """Test claiming a task moves its QA to session."""
    task_id = "T-2"
    qa_id = f"{task_id}-qa"
    session_id = "sess-1"

    todo_state = get_semantic_state("task", "todo")
    waiting_state = get_semantic_state("qa", "waiting")

    create_task_file(repo_env, task_id, state=todo_state)
    create_qa_file(repo_env, qa_id, task_id, state=waiting_state)

    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act
    workflow.claim_task(task_id, session_id)

    # Assert QA moved
    qa = qa_repo.get(qa_id)
    assert qa is not None, "QA should be loadable"
    assert qa.session_id == session_id

    # Verify QA file location
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / waiting_state / f"{qa_id}.md"
    assert expected_path.exists(), "QA should be moved to session directory"

    # Verify old file gone
    old_path = repo_env / ".project" / "qa" / waiting_state / f"{qa_id}.md"
    assert not old_path.exists(), "QA should be removed from global directory"

def test_complete_task_moves_from_wip_to_done(repo_env):
    """Test completing a task moves it to done."""
    task_id = "T-3"
    session_id = "sess-1"

    wip_state = get_semantic_state("task", "wip")
    done_state = get_semantic_state("task", "done")

    # Create task in session wip
    create_task_file(repo_env, task_id, state=wip_state, session_id=session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    updated_task = workflow.complete_task(task_id, session_id)

    # Assert
    assert updated_task.state == done_state

    # Verify file location
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "tasks" / done_state / f"{task_id}.md"
    assert expected_path.exists()

def test_complete_task_advances_qa_state(repo_env):
    """Test completing a task advances QA from waiting to todo."""
    task_id = "T-4"
    qa_id = f"{task_id}-qa"
    session_id = "sess-1"

    wip_state = get_semantic_state("task", "wip")
    waiting_state = get_semantic_state("qa", "waiting")
    qa_todo_state = get_semantic_state("qa", "todo")

    create_task_file(repo_env, task_id, state=wip_state, session_id=session_id)
    create_qa_file(repo_env, qa_id, task_id, state=waiting_state, session_id=session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)
    qa_repo = QARepository(project_root=repo_env)

    # Act
    workflow.complete_task(task_id, session_id)

    # Assert QA state
    qa = qa_repo.get(qa_id)
    assert qa.state == qa_todo_state

    # Verify QA file location
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / qa_todo_state / f"{qa_id}.md"
    assert expected_path.exists()

def test_claim_task_error_task_not_found(repo_env):
    """Test error when claiming non-existent task."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    with pytest.raises(PersistenceError, match="Task not found"):
        workflow.claim_task("NONEXISTENT", "sess-1")

def test_claim_task_fails_when_task_already_done(repo_env):
    """Test claim_task raises PersistenceError when task is already done."""
    task_id = "T-5"
    session_id = "sess-claim-5"

    # Create task in done state
    done_state = get_semantic_state("task", "done")
    create_task_file(repo_env, task_id, state=done_state)

    workflow = TaskQAWorkflow(project_root=repo_env)

    with pytest.raises(PersistenceError, match=f"Task {task_id} is already {done_state}"):
        workflow.claim_task(task_id, session_id)

def test_complete_task_not_found_raises_error(repo_env):
    """Test complete_task raises error when task doesn't exist."""
    workflow = TaskQAWorkflow(project_root=repo_env)

    with pytest.raises(PersistenceError, match="Task not found"):
        workflow.complete_task("nonexistent-task", "sess-1")

def test_claim_task_fails_when_task_already_validated(repo_env):
    """Test claim_task raises PersistenceError when task is validated."""
    task_id = "T-6"
    session_id = "sess-claim-6"

    # Create task in validated state
    validated_state = get_semantic_state("task", "validated")
    create_task_file(repo_env, task_id, state=validated_state)

    workflow = TaskQAWorkflow(project_root=repo_env)

    with pytest.raises(PersistenceError, match=f"Task {task_id} is already {validated_state}"):
        workflow.claim_task(task_id, session_id)

def test_complete_task_not_in_wip_raises_error(repo_env):
    """Test complete_task raises error if task not in wip state."""
    task_id = "T-7"
    session_id = "sess-1"

    # Create task in todo state (not wip)
    todo_state = get_semantic_state("task", "todo")
    create_task_file(repo_env, task_id, state=todo_state, session_id=session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Try to complete it - should raise error since it's not in wip state
    # The implementation should validate that task is in wip before completing
    with pytest.raises(PersistenceError):
        workflow.complete_task(task_id, session_id)

def test_complete_task_wrong_session_raises_error(repo_env):
    """Test complete_task validates session context."""
    task_id = "T-8"
    session_a = "sess-a"
    session_b = "sess-b"

    # Task claimed by session A and in wip state
    wip_state = get_semantic_state("task", "wip")
    create_task_file(repo_env, task_id, state=wip_state, session_id=session_a)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Try to complete with session B - should raise error
    # The implementation should validate that the session matches
    with pytest.raises(PersistenceError):
        workflow.complete_task(task_id, session_b)

def test_complete_task_returns_updated_task(repo_env):
    """Test complete_task returns Task with done state."""
    task_id = "T-9"
    session_id = "sess-1"

    wip_state = get_semantic_state("task", "wip")
    done_state = get_semantic_state("task", "done")

    # Create task in session wip
    original_task = create_task_file(repo_env, task_id, state=wip_state, session_id=session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act
    updated_task = workflow.complete_task(task_id, session_id)

    # Assert - returned task has correct state
    assert updated_task is not None
    assert updated_task.id == task_id
    assert updated_task.state == done_state
    assert updated_task.session_id == session_id
    assert updated_task.title == original_task.title

    # Verify state transition was recorded
    assert len(updated_task.state_history) > 0
    last_transition = updated_task.state_history[-1]
    assert last_transition.from_state == wip_state
    assert last_transition.to_state == done_state
    assert last_transition.reason == "completed"

def test_complete_task_handles_missing_qa_gracefully(repo_env):
    """Test completing task without associated QA doesn't fail."""
    task_id = "T-10"
    session_id = "sess-1"

    wip_state = get_semantic_state("task", "wip")
    done_state = get_semantic_state("task", "done")

    # Create task without QA
    create_task_file(repo_env, task_id, state=wip_state, session_id=session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Act - should complete successfully without QA
    updated_task = workflow.complete_task(task_id, session_id)

    # Assert
    assert updated_task.state == done_state

def test_claim_task_handles_missing_qa_gracefully(repo_env):
    """Test claim_task works even when there's no associated QA file."""
    task_id = "T-11"
    session_id = "sess-claim-11"

    todo_state = get_semantic_state("task", "todo")
    wip_state = get_semantic_state("task", "wip")

    # Create task WITHOUT QA
    create_task_file(repo_env, task_id, state=todo_state)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Should succeed without error
    claimed_task = workflow.claim_task(task_id, session_id)

    assert claimed_task.state == wip_state
    assert claimed_task.session_id == session_id

def test_claim_task_from_wip_to_wip_with_new_session(repo_env):
    """Test claiming a task that's already in wip (session switch scenario)."""
    task_id = "T-12"
    old_session_id = "sess-old"
    new_session_id = "sess-new"

    wip_state = get_semantic_state("task", "wip")

    # Create task in old session's wip
    create_task_file(repo_env, task_id, state=wip_state, session_id=old_session_id)

    workflow = TaskQAWorkflow(project_root=repo_env)

    # Claim with new session
    claimed_task = workflow.claim_task(task_id, new_session_id)

    # Should now be in new session's wip
    new_session_path = (
        repo_env / ".project" / "sessions" / "wip" / new_session_id / "tasks" / wip_state / f"{task_id}.md"
    )
    assert new_session_path.exists(), "Task should be in new session's wip"

    # Old location should be gone
    old_session_path = (
        repo_env / ".project" / "sessions" / "wip" / old_session_id / "tasks" / wip_state / f"{task_id}.md"
    )
    assert not old_session_path.exists(), "Task should be removed from old session"
    assert claimed_task.session_id == new_session_id

