"""Tests for unified state validation across all domains.

This module verifies that all entity types (session, task, qa) use the same
StateValidator and validation logic for state transitions. This ensures:
- Consistent validation behavior across domains
- No duplicate validation logic
- Single source of truth for state rules
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import pytest
import yaml

from edison.core.state.validator import StateValidator, MissingStateMachine
from edison.core.state.transitions import validate_transition, EntityTransitionError
from edison.core.state import StateTransitionError
from edison.core.session.persistence.repository import SessionRepository
from edison.core.task.repository import TaskRepository
from edison.core.qa.workflow.repository import QARepository
from edison.core.session.core.models import Session
from edison.core.task.models import Task
from edison.core.qa.models import QARecord
from edison.core.entity import EntityMetadata, EntityStateError
from tests.helpers.env_setup import setup_project_root
from tests.helpers.cache_utils import reset_edison_caches


@pytest.fixture
def unified_state_config(tmp_path: Path, monkeypatch):
    """Setup unified state machine configuration for all domains.

    This creates a complete state machine config that will be used
    by StateValidator, validate_transition, and all repositories.
    """
    # Reset caches
    reset_edison_caches()

    # Create config directory
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)
    (tmp_path / ".project").mkdir(exist_ok=True)

    # Create defaults
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    # Create session configuration (required for SessionRepository)
    session_config = {
        "session": {
            "paths": {
                "root": ".project/sessions",
                "archive": ".project/archive",
                "tx": ".project/tx",
            },
            "states": {
                "active": "wip",
                "closing": "closing",
                "closed": "done",
            },
            "lookupOrder": ["active", "closing", "closed"],
            "defaults": {
                "initialState": "active"
            },
        },
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_config))

    # Create unified state machine configuration
    state_machine = {
        "statemachine": {
            # Session states
            "session": {
                "states": {
                    "active": {
                        "initial": True,
                        "allowed_transitions": [
                            {"to": "closing"},
                            {"to": "active"},  # Self-transition
                        ],
                    },
                    "closing": {
                        "allowed_transitions": [
                            {"to": "closed"},
                        ],
                    },
                    "closed": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                },
            },
            # Task states
            "task": {
                "states": {
                    "todo": {
                        "initial": True,
                        "allowed_transitions": [
                            {"to": "wip"},
                            {"to": "todo"},  # Self-transition
                        ],
                    },
                    "wip": {
                        "allowed_transitions": [
                            {"to": "done"},
                            {"to": "todo"},  # Can go back to todo
                        ],
                    },
                    "done": {
                        "allowed_transitions": [
                            {"to": "validated"},
                        ],
                    },
                    "validated": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                },
            },
            # QA states
            "qa": {
                "states": {
                    "waiting": {
                        "initial": True,
                        "allowed_transitions": [
                            {"to": "todo"},
                        ],
                    },
                    "todo": {
                        "allowed_transitions": [
                            {"to": "wip"},
                        ],
                    },
                    "wip": {
                        "allowed_transitions": [
                            {"to": "done"},
                        ],
                    },
                    "done": {
                        "allowed_transitions": [
                            {"to": "validated"},
                        ],
                    },
                    "validated": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                },
            },
        },
    }
    (config_dir / "state-machine.yml").write_text(yaml.dump(state_machine))

    # Set environment
    setup_project_root(monkeypatch, tmp_path)
    monkeypatch.setenv("project_ROOT", str(tmp_path))

    # Note: session.state module removed - state machine built on-demand from config

    yield tmp_path

    # Cleanup
    reset_edison_caches()


# ==============================================================================
# Test StateValidator directly
# ==============================================================================

def test_state_validator_session_allows_valid_transition(unified_state_config: Path) -> None:
    """StateValidator allows valid session state transitions.
    
    Uses recovery->active transition with always_allow guard.
    """
    validator = StateValidator(repo_root=unified_state_config)

    # recovery -> active has always_allow guard in production
    validator.ensure_transition("session", "recovery", "active")


def test_state_validator_session_blocks_invalid_transition(unified_state_config: Path) -> None:
    """StateValidator blocks invalid session state transitions."""
    validator = StateValidator(repo_root=unified_state_config)

    # Cannot skip closing and go directly to closed
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("session", "active", "closed")


def test_state_validator_task_allows_valid_transition(unified_state_config: Path) -> None:
    """StateValidator allows valid task state transitions.
    
    Uses transitions with always_allow guards from production config.
    """
    validator = StateValidator(repo_root=unified_state_config)

    # wip -> todo has always_allow guard in production
    validator.ensure_transition("task", "wip", "todo")


def test_state_validator_task_blocks_invalid_transition(unified_state_config: Path) -> None:
    """StateValidator blocks invalid task state transitions."""
    validator = StateValidator(repo_root=unified_state_config)

    # Cannot go from todo directly to validated (skips wip and done)
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("task", "todo", "validated")


def test_state_validator_qa_allows_valid_transition(unified_state_config: Path) -> None:
    """StateValidator allows valid QA state transitions.
    
    Uses transitions with always_allow guards from production config.
    """
    validator = StateValidator(repo_root=unified_state_config)

    # todo -> wip and wip -> todo have always_allow guards in production
    validator.ensure_transition("qa", "todo", "wip")
    validator.ensure_transition("qa", "wip", "todo")


def test_state_validator_qa_blocks_invalid_transition(unified_state_config: Path) -> None:
    """StateValidator blocks invalid QA state transitions."""
    validator = StateValidator(repo_root=unified_state_config)

    # Cannot go from waiting directly to wip
    with pytest.raises(StateTransitionError):
        validator.ensure_transition("qa", "waiting", "wip")


def test_state_validator_rejects_unknown_entity(unified_state_config: Path) -> None:
    """StateValidator raises MissingStateMachine for unknown entity types."""
    validator = StateValidator(repo_root=unified_state_config)

    with pytest.raises(MissingStateMachine, match="unknown_entity"):
        validator.ensure_transition("unknown_entity", "state1", "state2")


# ==============================================================================
# Test validate_transition function (used by repositories)
# ==============================================================================

def test_validate_transition_session_accepts_valid(unified_state_config: Path) -> None:
    """validate_transition accepts valid session transitions.
    
    Uses recovery->active transition with always_allow guard.
    """
    valid, error = validate_transition("session", "recovery", "active")

    assert valid is True
    assert error == ""


def test_validate_transition_session_rejects_invalid(unified_state_config: Path) -> None:
    """validate_transition rejects invalid session transitions."""
    valid, error = validate_transition("session", "active", "closed")

    assert valid is False
    assert "not allowed" in error.lower()


def test_validate_transition_task_accepts_valid(unified_state_config: Path) -> None:
    """validate_transition accepts valid task transitions.
    
    Uses wip->todo transition with always_allow guard.
    """
    valid, error = validate_transition("task", "wip", "todo")

    assert valid is True
    assert error == ""


def test_validate_transition_task_rejects_invalid(unified_state_config: Path) -> None:
    """validate_transition rejects invalid task transitions."""
    valid, error = validate_transition("task", "todo", "validated")

    assert valid is False
    assert "not allowed" in error.lower()


def test_validate_transition_qa_accepts_valid(unified_state_config: Path) -> None:
    """validate_transition accepts valid QA transitions.
    
    Uses todo->wip transition with always_allow guard.
    """
    valid, error = validate_transition("qa", "todo", "wip")

    assert valid is True
    assert error == ""


def test_validate_transition_qa_rejects_invalid(unified_state_config: Path) -> None:
    """validate_transition rejects invalid QA transitions."""
    valid, error = validate_transition("qa", "waiting", "done")

    assert valid is False
    assert "not allowed" in error.lower()


def test_validate_transition_allows_self_transition(unified_state_config: Path) -> None:
    """validate_transition allows same-state transitions when declared."""
    # Session active -> active is declared
    valid, error = validate_transition("session", "active", "active")
    assert valid is True

    # Task todo -> todo is declared
    valid, error = validate_transition("task", "todo", "todo")
    assert valid is True


# ==============================================================================
# Test Repository.transition() method (all domains)
# ==============================================================================

def test_session_repository_transition_uses_validation(unified_state_config: Path) -> None:
    """SessionRepository.transition() uses unified state validation.
    
    Note: Uses active state since that's the default initial state.
    Tests that valid transitions pass through validation.
    """
    repo = SessionRepository(project_root=unified_state_config)

    # Create a session in active state (default initial state)
    session = Session.create("test-session", state="active")
    repo.create(session)

    # Self-transition is always allowed
    updated = repo.transition("test-session", "active")
    assert updated.state == "active"

    # Reload to verify persistence
    reloaded = repo.get("test-session")
    assert reloaded is not None
    assert reloaded.state == "active"


def test_session_repository_transition_rejects_invalid(unified_state_config: Path) -> None:
    """SessionRepository.transition() rejects invalid transitions."""
    repo = SessionRepository(project_root=unified_state_config)

    # Create a session in active state
    session = Session.create("test-session-2", state="active")
    repo.create(session)

    # Invalid transition should raise EntityStateError
    with pytest.raises(EntityStateError, match="not allowed"):
        repo.transition("test-session-2", "closed")


def test_task_repository_transition_uses_validation(unified_state_config: Path) -> None:
    """TaskRepository.transition() uses unified state validation.
    
    Uses wip->todo transition with always_allow guard.
    """
    repo = TaskRepository(project_root=unified_state_config)

    # Create a task in wip state
    task = Task(
        id="T-001",
        state="wip",
        title="Test Task",
        description="Test description",
        metadata=EntityMetadata.create(),
    )
    repo.create(task)

    # Valid transition (wip -> todo has always_allow) should succeed
    updated = repo.transition("T-001", "todo")
    assert updated.state == "todo"

    # Reload to verify
    reloaded = repo.get("T-001")
    assert reloaded is not None
    assert reloaded.state == "todo"


def test_task_repository_transition_rejects_invalid(unified_state_config: Path) -> None:
    """TaskRepository.transition() rejects invalid transitions."""
    repo = TaskRepository(project_root=unified_state_config)

    # Create a task in todo state
    task = Task(
        id="T-002",
        state="todo",
        title="Test Task 2",
        description="Test description",
        metadata=EntityMetadata.create(),
    )
    repo.create(task)

    # Invalid transition (skipping wip to go directly to validated)
    with pytest.raises(EntityStateError, match="not allowed"):
        repo.transition("T-002", "validated")


def test_qa_repository_advance_state_workflow_method(unified_state_config: Path) -> None:
    """QARepository.advance_state() uses state validation with guards.

    Note: advance_state() now uses transition_entity() which enforces guards.
    Use todo->wip transition which has always_allow guard.
    """
    repo = QARepository(project_root=unified_state_config)

    # Create a QA record in todo state
    qa = QARecord(
        id="T-001-qa",
        task_id="T-001",
        state="todo",
        title="QA for T-001",
        metadata=EntityMetadata.create(),
    )
    repo.create(qa)

    # advance_state uses transition_entity which enforces guards
    # todo->wip has always_allow guard
    updated = repo.advance_state("T-001-qa", "wip")
    assert updated.state == "wip"

    # Reload to verify
    reloaded = repo.get("T-001-qa")
    assert reloaded is not None
    assert reloaded.state == "wip"


def test_qa_repository_transition_uses_validation(unified_state_config: Path) -> None:
    """QARepository.transition() uses unified state validation.
    
    Uses todo->wip transition with always_allow guard.
    """
    # QARepository inherits transition() from BaseRepository
    # which uses validate_transition
    repo = QARepository(project_root=unified_state_config)

    # Create a QA record in todo state
    qa = QARecord(
        id="T-002-qa",
        task_id="T-002",
        state="todo",
        title="QA for T-002",
        metadata=EntityMetadata.create(),
    )
    repo.create(qa)

    # Valid transition via inherited transition() method (todo->wip has always_allow)
    updated = repo.transition("T-002-qa", "wip")
    assert updated.state == "wip"

    # Invalid transition (skipping done to validated) should fail
    with pytest.raises(EntityStateError, match="not allowed"):
        repo.transition("T-002-qa", "validated")


# ==============================================================================
# Test consistency: All domains reject same invalid pattern
# ==============================================================================

def test_all_domains_reject_invalid_transitions_consistently(unified_state_config: Path) -> None:
    """All domains (session, task, qa) reject invalid transitions with same error type."""
    # Session: active -> closed (invalid)
    valid_session, error_session = validate_transition("session", "active", "closed")
    assert valid_session is False

    # Task: todo -> validated (invalid)
    valid_task, error_task = validate_transition("task", "todo", "validated")
    assert valid_task is False

    # QA: waiting -> validated (invalid)
    valid_qa, error_qa = validate_transition("qa", "waiting", "validated")
    assert valid_qa is False

    # All should have similar error messages
    assert "not allowed" in error_session.lower()
    assert "not allowed" in error_task.lower()
    assert "not allowed" in error_qa.lower()


def test_all_domains_use_same_validation_path(unified_state_config: Path) -> None:
    """Verify all domains use the same state machine configuration source.

    This test verifies that:
    1. StateValidator reads from config
    2. validate_transition reads from config

    Therefore all use the same source of truth.
    Uses transitions with always_allow guards to test validation path.
    """
    validator = StateValidator(repo_root=unified_state_config)

    # Test that StateValidator and validate_transition produce same results for valid transitions
    # For session (recovery -> active has always_allow)
    validator.ensure_transition("session", "recovery", "active")
    valid, _ = validate_transition("session", "recovery", "active")
    assert valid is True

    # For task (wip -> todo has always_allow)
    validator.ensure_transition("task", "wip", "todo")
    valid, _ = validate_transition("task", "wip", "todo")
    assert valid is True

    # For QA (todo -> wip has always_allow)
    validator.ensure_transition("qa", "todo", "wip")
    valid, _ = validate_transition("qa", "todo", "wip")
    assert valid is True

    # Test that BOTH StateValidator and validate_transition reject invalid transitions consistently
    # Task: todo -> validated (skips wip, done)
    validator_error = None
    try:
        validator.ensure_transition("task", "todo", "validated")
    except StateTransitionError as e:
        validator_error = str(e)
    
    valid, api_error = validate_transition("task", "todo", "validated")
    
    # Both should reject this invalid transition
    assert validator_error is not None, "StateValidator should reject todo->validated"
    assert valid is False, "validate_transition should reject todo->validated"
    assert "not allowed" in api_error.lower()


# ==============================================================================
# Integration test: End-to-end workflow validation
# ==============================================================================

def test_end_to_end_workflow_respects_state_machine(unified_state_config: Path) -> None:
    """End-to-end test: Workflow respects state machine using always_allow transitions.
    
    This tests the state machine validation path, not guard logic.
    Uses transitions with always_allow guards where possible.
    """
    task_repo = TaskRepository(project_root=unified_state_config)
    qa_repo = QARepository(project_root=unified_state_config)

    # 1. Create task in wip state (for always_allow transitions)
    task = Task(
        id="T-WORKFLOW",
        state="wip",
        title="Workflow Task",
        description="Test workflow",
        metadata=EntityMetadata.create(),
    )
    task_repo.create(task)

    # 2. Create QA in todo state (for always_allow transitions)
    qa = QARecord(
        id="T-WORKFLOW-qa",
        task_id="T-WORKFLOW",
        state="todo",
        title="QA for workflow",
        metadata=EntityMetadata.create(),
    )
    qa_repo.create(qa)

    # 3. Transition task: wip -> todo (always_allow)
    task_repo.transition("T-WORKFLOW", "todo")

    # 4. Transition QA: todo -> wip (always_allow)
    qa_repo.advance_state("T-WORKFLOW-qa", "wip")

    # 5. Transition QA: wip -> todo (always_allow - rollback path)
    qa_repo.advance_state("T-WORKFLOW-qa", "todo")

    # 6. Try invalid task transition: todo -> validated (skips states)
    with pytest.raises(EntityStateError):
        task_repo.transition("T-WORKFLOW", "validated")

    # Verify final states
    final_task = task_repo.get("T-WORKFLOW")
    final_qa = qa_repo.get("T-WORKFLOW-qa")

    assert final_task is not None, "Task should exist after transitions"
    assert final_task.state == "todo", f"Task should be 'todo' but is '{final_task.state}'"
    assert final_qa is not None, "QA should exist after transitions"
    assert final_qa.state == "todo", f"QA should be 'todo' but is '{final_qa.state}'"
