"""Tests for QARepository workflow methods.

These tests validate advance_state() high-level workflow.
"""
import pytest
from helpers.io_utils import write_yaml
import importlib
from pathlib import Path
from edison.core.qa.repository import QARepository
from edison.core.entity import PersistenceError, EntityMetadata
from edison.core.qa.models import QARecord

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
                "qa": {
                    "states": {
                        "waiting": {"allowed_transitions": [{"to": "todo"}]},
                        "todo": {"allowed_transitions": [{"to": "wip"}]},
                        "wip": {"allowed_transitions": [{"to": "done"}]},
                        "done": {"allowed_transitions": [{"to": "validated"}]},
                        "validated": {"allowed_transitions": []},
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

def test_advance_state_moves_qa_to_new_state(repo_env):
    """Test advance_state moves QA record to new state directory."""
    qa_id = "T-1-qa"
    task_id = "T-1"

    # Create QA in waiting state (global)
    create_qa_file(repo_env, qa_id, task_id, state="waiting")

    repo = QARepository(project_root=repo_env)

    # Act - advance from waiting to todo
    updated_qa = repo.advance_state(qa_id, "todo")

    # Assert - QA state updated
    assert updated_qa.state == "todo"
    assert updated_qa.id == qa_id
    assert updated_qa.task_id == task_id

    # Verify file moved to new directory
    expected_path = repo_env / ".project" / "qa" / "todo" / f"{qa_id}.md"
    assert expected_path.exists()

    # Verify old file removed
    old_path = repo_env / ".project" / "qa" / "waiting" / f"{qa_id}.md"
    assert not old_path.exists()

    # Verify we can retrieve it from new location
    reloaded_qa = repo.get(qa_id)
    assert reloaded_qa is not None
    assert reloaded_qa.state == "todo"

def test_advance_state_with_session(repo_env):
    """Test advance_state works within session context."""
    qa_id = "T-2-qa"
    task_id = "T-2"
    session_id = "sess-1"

    # Create QA in session qa/waiting
    create_qa_file(repo_env, qa_id, task_id, state="waiting", session_id=session_id)

    repo = QARepository(project_root=repo_env)

    # Act - advance from waiting to todo within session
    updated_qa = repo.advance_state(qa_id, "todo", session_id=session_id)

    # Assert - QA state updated with session
    assert updated_qa.state == "todo"
    assert updated_qa.session_id == session_id

    # Verify file moved within session directory
    expected_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / "todo" / f"{qa_id}.md"
    assert expected_path.exists()

    # Verify old file removed
    old_path = repo_env / ".project" / "sessions" / "wip" / session_id / "qa" / "waiting" / f"{qa_id}.md"
    assert not old_path.exists()

def test_advance_state_records_transition(repo_env):
    """Test advance_state records state transition in history."""
    qa_id = "T-3-qa"
    task_id = "T-3"

    # Create QA in waiting state
    create_qa_file(repo_env, qa_id, task_id, state="waiting")

    repo = QARepository(project_root=repo_env)

    # Act - advance state
    updated_qa = repo.advance_state(qa_id, "todo")

    # Assert - state history contains the transition
    assert len(updated_qa.state_history) > 0

    # Find the transition entry
    transition = updated_qa.state_history[-1]  # Most recent transition
    assert transition.from_state == "waiting"
    assert transition.to_state == "todo"
    assert transition.reason == "workflow_advance"
    assert transition.timestamp is not None

def test_advance_state_returns_updated_record(repo_env):
    """Test advance_state returns QARecord with new state."""
    qa_id = "T-4-qa"
    task_id = "T-4"

    # Create QA in waiting state
    create_qa_file(repo_env, qa_id, task_id, state="waiting")

    repo = QARepository(project_root=repo_env)

    # Act
    updated_qa = repo.advance_state(qa_id, "todo")

    # Assert - returned record has all expected properties
    assert isinstance(updated_qa, QARecord)
    assert updated_qa.id == qa_id
    assert updated_qa.task_id == task_id
    assert updated_qa.state == "todo"
    assert updated_qa.title == f"QA {task_id}"
    assert updated_qa.metadata is not None

def test_advance_state_multiple_transitions(repo_env):
    """Test advance_state through multiple state transitions."""
    qa_id = "T-5-qa"
    task_id = "T-5"

    # Create QA in waiting state
    create_qa_file(repo_env, qa_id, task_id, state="waiting")

    repo = QARepository(project_root=repo_env)

    # Transition 1: waiting -> todo
    qa1 = repo.advance_state(qa_id, "todo")
    assert qa1.state == "todo"
    assert len(qa1.state_history) >= 1

    # Transition 2: todo -> wip
    qa2 = repo.advance_state(qa_id, "wip")
    assert qa2.state == "wip"
    assert len(qa2.state_history) >= 2

    # Transition 3: wip -> done
    qa3 = repo.advance_state(qa_id, "done")
    assert qa3.state == "done"
    assert len(qa3.state_history) >= 3

    # Verify final file location
    expected_path = repo_env / ".project" / "qa" / "done" / f"{qa_id}.md"
    assert expected_path.exists()

def test_advance_state_error_qa_not_found(repo_env):
    """Test error when advancing non-existent QA."""
    repo = QARepository(project_root=repo_env)

    with pytest.raises(PersistenceError, match="QA record not found"):
        repo.advance_state("NONEXISTENT-qa", "todo")

def test_advance_state_changes_session_ownership(repo_env):
    """Test advance_state can change session ownership."""
    qa_id = "T-6-qa"
    task_id = "T-6"

    # Create QA in global waiting state (no session)
    create_qa_file(repo_env, qa_id, task_id, state="waiting", session_id=None)

    repo = QARepository(project_root=repo_env)

    # Advance to todo and assign to session
    updated_qa = repo.advance_state(qa_id, "todo", session_id="sess-1")

    # Assert - session ownership updated
    assert updated_qa.session_id == "sess-1"

    # Verify file moved to session directory
    expected_path = repo_env / ".project" / "sessions" / "wip" / "sess-1" / "qa" / "todo" / f"{qa_id}.md"
    assert expected_path.exists()

def test_advance_state_preserves_metadata(repo_env):
    """Test advance_state preserves QA metadata."""
    qa_id = "T-7-qa"
    task_id = "T-7"

    # Create QA with specific metadata
    original_qa = create_qa_file(repo_env, qa_id, task_id, state="waiting")
    original_created_at = original_qa.metadata.created_at

    repo = QARepository(project_root=repo_env)

    # Advance state
    updated_qa = repo.advance_state(qa_id, "todo")

    # Assert - metadata preserved but updated_at changed
    assert updated_qa.metadata.created_at == original_created_at
    assert updated_qa.metadata.created_by == "test"
    assert updated_qa.metadata.updated_at is not None

def test_advance_state_preserves_round_number(repo_env):
    """Test advance_state preserves round number."""
    qa_id = "T-8-qa"
    task_id = "T-8"

    # Create QA with specific round
    repo = QARepository(project_root=repo_env)
    qa = QARecord(
        id=qa_id,
        task_id=task_id,
        state="waiting",
        title=f"QA {task_id}",
        round=3,
        metadata=EntityMetadata.create(created_by="test")
    )
    repo.save(qa)

    # Advance state
    updated_qa = repo.advance_state(qa_id, "todo")

    # Assert - round number preserved
    assert updated_qa.round == 3
