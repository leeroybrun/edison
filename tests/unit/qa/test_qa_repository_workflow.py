"""Tests for QARepository workflow methods.

These tests validate advance_state() high-level workflow.

NOTE: Tests use transitions with `always_allow` guards (todo->wip, wip->todo)
to test workflow mechanics without testing guard logic. Guard-specific tests
are in test_qa_guards.py.
"""
import pytest
from helpers.io_utils import write_yaml
from helpers.fixtures import create_qa_file
import importlib
from pathlib import Path
from edison.core.qa.workflow.repository import QARepository
from edison.core.entity import PersistenceError, EntityMetadata
from edison.core.qa.models import QARecord
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.cache_utils import reset_edison_caches

@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup a repository environment with configuration.
    
    Uses state machine config with always_allow guards for workflow testing.
    """
    from tests.helpers.fixtures import create_repo_with_git
    repo = create_repo_with_git(tmp_path)
    config_dir = repo / ".edison" / "config"

    # 1. defaults.yaml (State Machine with always_allow guards for workflow tests)
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "qa": {
                    "states": {
                        "waiting": {
                            "initial": True,
                            "allowed_transitions": [
                                {"to": "todo", "guard": "always_allow"},
                            ]
                        },
                        "todo": {
                            "allowed_transitions": [
                                {"to": "wip", "guard": "always_allow"},
                            ]
                        },
                        "wip": {
                            "allowed_transitions": [
                                {"to": "done", "guard": "always_allow"},
                                {"to": "todo", "guard": "always_allow"},
                            ]
                        },
                        "done": {
                            "allowed_transitions": [
                                {"to": "validated", "guard": "always_allow"},
                                {"to": "wip", "guard": "always_allow"},
                            ]
                        },
                        "validated": {
                            "final": True,
                            "allowed_transitions": []
                        },
                    }
                }
            }
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

    # 3. workflow.yaml
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
            },
            # Override state machine for tests with always_allow guards
            "statemachine": {
                "qa": {
                    "states": {
                        "waiting": {
                            "initial": True,
                            "allowed_transitions": [
                                {"to": "todo", "guard": "always_allow"},
                            ]
                        },
                        "todo": {
                            "allowed_transitions": [
                                {"to": "wip", "guard": "always_allow"},
                            ]
                        },
                        "wip": {
                            "allowed_transitions": [
                                {"to": "done", "guard": "always_allow"},
                                {"to": "todo", "guard": "always_allow"},
                            ]
                        },
                        "done": {
                            "allowed_transitions": [
                                {"to": "validated", "guard": "always_allow"},
                                {"to": "wip", "guard": "always_allow"},
                            ]
                        },
                        "validated": {
                            "final": True,
                            "allowed_transitions": []
                        },
                    }
                }
            }
        }
    )

    # 4. state-machine.yaml
    write_yaml(
        config_dir / "state-machine.yaml",
        {
            "statemachine": {
                "qa": {"states": ["waiting", "todo", "wip", "done", "validated"]}
            }
        }
    )

    setup_project_root(monkeypatch, repo)

    # Reset caches to pick up new config
    reset_edison_caches()

    # Reload config-dependent modules
    import edison.core.config.domains.task as task_config
    importlib.reload(task_config)
    import edison.core.task.paths as paths
    importlib.reload(paths)
    import edison.core.config.domains.workflow as wf
    importlib.reload(wf)

    return repo


def test_advance_state_moves_qa_to_new_state(repo_env):
    """Test advance_state moves QA record to new state directory.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-1-qa"
    task_id = "T-1"

    # Create QA in todo state (uses always_allow guard for todo->wip)
    create_qa_file(repo_env, qa_id, task_id, state="todo")

    repo = QARepository(project_root=repo_env)

    # Act - advance from todo to wip (always_allow guard)
    updated_qa = repo.advance_state(qa_id, "wip")

    # Assert - QA state updated
    assert updated_qa.state == "wip"
    assert updated_qa.id == qa_id
    assert updated_qa.task_id == task_id

    # Verify file moved to new directory
    expected_path = repo_env / ".project" / "qa" / "wip" / f"{qa_id}.md"
    assert expected_path.exists()

    # Verify old file removed
    old_path = repo_env / ".project" / "qa" / "todo" / f"{qa_id}.md"
    assert not old_path.exists()

    # Verify we can retrieve it from new location
    reloaded_qa = repo.get(qa_id)
    assert reloaded_qa is not None
    assert reloaded_qa.state == "wip"

def test_advance_state_with_session(repo_env):
    """Test advance_state works within session context.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-2-qa"
    task_id = "T-2"
    session_id = "sess-1"

    # Create QA in session qa/todo
    create_qa_file(repo_env, qa_id, task_id, state="todo", session_id=session_id)

    repo = QARepository(project_root=repo_env)

    # Act - advance from todo to wip within session
    updated_qa = repo.advance_state(qa_id, "wip", session_id=session_id)

    # Assert - QA state updated with session
    assert updated_qa.state == "wip"
    assert updated_qa.session_id == session_id

    # Verify file moved within session directory
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / "wip" / f"{qa_id}.md"
    assert expected_path.exists()

    # Verify old file removed
    old_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / "todo" / f"{qa_id}.md"
    assert not old_path.exists()

def test_advance_state_records_transition(repo_env):
    """Test advance_state records state transition in history.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-3-qa"
    task_id = "T-3"

    # Create QA in todo state
    create_qa_file(repo_env, qa_id, task_id, state="todo")

    repo = QARepository(project_root=repo_env)

    # Act - advance state
    updated_qa = repo.advance_state(qa_id, "wip")

    # Assert - state history contains the transition
    assert len(updated_qa.state_history) > 0

    # Find the transition entry
    transition = updated_qa.state_history[-1]  # Most recent transition
    assert transition.from_state == "todo"
    assert transition.to_state == "wip"
    assert transition.timestamp is not None

def test_advance_state_returns_updated_record(repo_env):
    """Test advance_state returns QARecord with new state.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-4-qa"
    task_id = "T-4"

    # Create QA in todo state
    create_qa_file(repo_env, qa_id, task_id, state="todo")

    repo = QARepository(project_root=repo_env)

    # Act
    updated_qa = repo.advance_state(qa_id, "wip")

    # Assert - returned record has all expected properties
    assert isinstance(updated_qa, QARecord)
    assert updated_qa.id == qa_id
    assert updated_qa.task_id == task_id
    assert updated_qa.state == "wip"
    assert updated_qa.title == f"QA {task_id}"
    assert updated_qa.metadata is not None

def test_advance_state_multiple_transitions(repo_env):
    """Test advance_state through multiple state transitions.
    
    Uses transitions with always_allow guards from production config:
    - todo -> wip (always_allow)
    - wip -> todo (always_allow) - rollback path
    - todo -> wip (always_allow) - forward again
    """
    qa_id = "T-5-qa"
    task_id = "T-5"

    # Create QA in todo state
    create_qa_file(repo_env, qa_id, task_id, state="todo")

    repo = QARepository(project_root=repo_env)

    # Transition 1: todo -> wip (always_allow in production)
    qa1 = repo.advance_state(qa_id, "wip")
    assert qa1.state == "wip"
    assert len(qa1.state_history) >= 1

    # Transition 2: wip -> todo (always_allow in production - rollback path)
    qa2 = repo.advance_state(qa_id, "todo")
    assert qa2.state == "todo"
    assert len(qa2.state_history) >= 2

    # Transition 3: todo -> wip (always_allow in production - forward again)
    qa3 = repo.advance_state(qa_id, "wip")
    assert qa3.state == "wip"
    assert len(qa3.state_history) >= 3

    # Verify final file location
    expected_path = repo_env / ".project" / "qa" / "wip" / f"{qa_id}.md"
    assert expected_path.exists()

def test_advance_state_error_qa_not_found(repo_env):
    """Test error when advancing non-existent QA."""
    repo = QARepository(project_root=repo_env)

    with pytest.raises(PersistenceError, match="QA record not found"):
        repo.advance_state("NONEXISTENT-qa", "wip")

def test_advance_state_changes_session_ownership(repo_env):
    """Test advance_state can change session ownership.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-6-qa"
    task_id = "T-6"

    # Create QA in global todo state (no session)
    create_qa_file(repo_env, qa_id, task_id, state="todo", session_id=None)

    repo = QARepository(project_root=repo_env)

    # Advance to wip and assign to session
    updated_qa = repo.advance_state(qa_id, "wip", session_id="sess-1")

    # Assert - session ownership updated
    assert updated_qa.session_id == "sess-1"

    # Verify file moved to session directory
    expected_path = repo_env / ".project" / "sessions" / "wip" / "sess-1" / "qa" / "wip" / f"{qa_id}.md"
    assert expected_path.exists()

def test_advance_state_preserves_metadata(repo_env):
    """Test advance_state preserves QA metadata.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-7-qa"
    task_id = "T-7"

    # Create QA with specific metadata
    original_qa = create_qa_file(repo_env, qa_id, task_id, state="todo")
    original_created_at = original_qa.metadata.created_at

    repo = QARepository(project_root=repo_env)

    # Advance state
    updated_qa = repo.advance_state(qa_id, "wip")

    # Assert - metadata preserved but updated_at changed
    assert updated_qa.metadata.created_at == original_created_at
    assert updated_qa.metadata.created_by == "test"
    assert updated_qa.metadata.updated_at is not None

def test_advance_state_preserves_round_number(repo_env):
    """Test advance_state preserves round number.
    
    Uses todo->wip transition with always_allow guard.
    """
    qa_id = "T-8-qa"
    task_id = "T-8"

    # Create QA with specific round in todo state
    repo = QARepository(project_root=repo_env)
    qa = QARecord(
        id=qa_id,
        task_id=task_id,
        state="todo",
        title=f"QA {task_id}",
        round=3,
        metadata=EntityMetadata.create(created_by="test")
    )
    repo.save(qa)

    # Advance state (todo->wip has always_allow guard)
    updated_qa = repo.advance_state(qa_id, "wip")

    # Assert - round number preserved
    assert updated_qa.round == 3
