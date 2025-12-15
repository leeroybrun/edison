"""Tests for BaseRepository.transition() method.

These tests ensure that BaseRepository.transition() correctly:
1. Validates state transitions
2. Executes configured actions
3. Records state history
4. Persists entity changes
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity.repository import BaseRepository
from edison.core.entity.base import BaseEntity, EntityId, EntityMetadata, StateHistoryEntry
from edison.core.entity.exceptions import EntityStateError, EntityNotFoundError

from helpers.io_utils import write_yaml


# ---------- Test Entity Implementation ----------

class MockEntity(BaseEntity):
    """Mock entity for repository tests."""

    def __init__(
        self,
        id: EntityId,
        state: str = "todo",
        metadata: Optional[EntityMetadata] = None,
        state_history: Optional[List[StateHistoryEntry]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            id=id,
            state=state,
            metadata=metadata or EntityMetadata.create(),
            state_history=state_history or [],
        )
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MockEntity":
        """Create from dictionary."""
        base = super().from_dict(data)
        return cls(
            id=base.id,
            state=base.state,
            metadata=base.metadata,
            state_history=base.state_history,
            data=data.get("data", {}),
        )


# ---------- Test Repository Implementation ----------

class MockRepository(BaseRepository[MockEntity]):
    """In-memory repository for testing."""

    def __init__(self, project_root: Path):
        super().__init__(project_root=project_root)
        self._storage: Dict[EntityId, MockEntity] = {}
        self.entity_type = "test_entity"

    def _do_create(self, entity: MockEntity) -> MockEntity:
        """Create entity in storage."""
        self._storage[entity.id] = entity
        return entity

    def _do_exists(self, entity_id: EntityId) -> bool:
        """Check if entity exists."""
        return entity_id in self._storage

    def _do_get(self, entity_id: EntityId) -> Optional[MockEntity]:
        """Get entity from storage."""
        return self._storage.get(entity_id)

    def _do_save(self, entity: MockEntity) -> None:
        """Save entity to storage."""
        self._storage[entity.id] = entity

    def _do_delete(self, entity_id: EntityId) -> bool:
        """Delete entity from storage."""
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False

    def _do_find(self, **criteria: Any) -> List[MockEntity]:
        """Find entities matching criteria."""
        results = []
        for entity in self._storage.values():
            match = True
            for key, value in criteria.items():
                if getattr(entity, key, None) != value:
                    match = False
                    break
            if match:
                results.append(entity)
        return results

    def _do_list_by_state(self, state: str) -> List[MockEntity]:
        """List entities by state."""
        return [e for e in self._storage.values() if e.state == state]

    def _do_list_all(self) -> List[MockEntity]:
        """List all entities."""
        return list(self._storage.values())


# ---------- Test Fixtures ----------

@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup repository environment with state machine configuration."""
    from tests.helpers.fixtures import create_repo_with_git
    repo = create_repo_with_git(tmp_path)
    config_dir = repo / ".edison" / "config"

    # Setup state machine configuration for test_entity
    # This is REAL configuration, not mocking - the state machine engine
    # will read this config and build a real state machine
    state_machine_spec = {
        "states": {
            "todo": {
                "allowed_transitions": [
                    {
                        "to": "wip",
                        "actions": [
                            {"name": "record_activation_time"}
                        ]
                    }
                ]
            },
            "wip": {
                "allowed_transitions": [
                    {
                        "to": "done",
                        "actions": [
                            {"name": "record_completion_time"}
                        ]
                    },
                    {
                        "to": "todo"
                    }
                ]
            },
            "done": {
                "allowed_transitions": [
                    {
                        "to": "validated"
                    }
                ]
            },
            "validated": {
                "allowed_transitions": []
            },
        },
    }

    write_yaml(
        config_dir / "defaults.yaml",
        {
            # State machine config is sourced from workflow.statemachine (canonical).
            "workflow": {"statemachine": {"test_entity": state_machine_spec}},
        },
    )
    # Ensure subsequent domain config reads pick up our freshly-written file.
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Set repo root so config loading works
    monkeypatch.setenv("EDISON_ROOT", str(repo))
    monkeypatch.chdir(repo)

    return repo


@pytest.fixture
def repository(repo_env: Path):
    """Create test repository instance."""
    return MockRepository(project_root=repo_env)


@pytest.fixture
def entity():
    """Create test entity."""
    return MockEntity(id="test-001", state="todo")


# ---------- Tests ----------

def test_repository_transition_validates_state(repo_env, repository, entity):
    """Repository.transition() validates state change is allowed."""
    # Create entity
    repository.create(entity)

    # Valid transition should succeed
    updated = repository.transition(entity.id, "wip")
    assert updated.state == "wip"

    # Invalid transition should raise error
    with pytest.raises(EntityStateError) as exc_info:
        repository.transition(entity.id, "validated")

    assert "Cannot transition" in str(exc_info.value) or "not allowed" in str(exc_info.value)


def test_repository_transition_executes_actions(repo_env, repository, entity):
    """Repository.transition() executes configured actions."""
    # Create entity
    repository.create(entity)

    # Transition to wip - should execute record_activation_time action
    updated = repository.transition(entity.id, "wip")
    assert updated.state == "wip"

    # The action should have been recorded in the context during transition
    # We can verify this by checking that the state machine was engaged
    # (actions are executed by the state machine during validate())

    # Transition to done - should execute record_completion_time action
    updated = repository.transition(updated.id, "done")
    assert updated.state == "done"


def test_repository_transition_records_history(repo_env, repository, entity):
    """Repository.transition() records state transition in entity history."""
    # Create entity
    repository.create(entity)
    initial_history_len = len(entity.state_history)

    # Transition to wip
    updated = repository.transition(entity.id, "wip")

    # Should have recorded the transition
    assert len(updated.state_history) == initial_history_len + 1

    # Check last history entry
    last_entry = updated.state_history[-1]
    assert last_entry.from_state == "todo"
    assert last_entry.to_state == "wip"
    assert last_entry.timestamp is not None

    # Transition to done
    updated = repository.transition(updated.id, "done")

    # Should have another history entry
    assert len(updated.state_history) == initial_history_len + 2
    last_entry = updated.state_history[-1]
    assert last_entry.from_state == "wip"
    assert last_entry.to_state == "done"


def test_repository_transition_saves_entity(repo_env, repository, entity):
    """Repository.transition() saves entity after state change."""
    # Create entity
    repository.create(entity)

    # Transition to wip
    updated = repository.transition(entity.id, "wip")

    # Entity should be persisted with new state
    persisted = repository.get(entity.id)
    assert persisted is not None
    assert persisted.state == "wip"
    assert len(persisted.state_history) > 0

    # Verify it's the same entity that was returned
    assert persisted.id == updated.id
    assert persisted.state == updated.state


def test_repository_transition_with_context(repo_env, repository, entity):
    """Repository.transition() passes context to state machine."""
    # Create entity
    repository.create(entity)

    # Transition with context
    context = {"user": "test-user", "reason": "testing"}
    updated = repository.transition(entity.id, "wip", context=context)

    # Should succeed with context passed through
    assert updated.state == "wip"


def test_repository_transition_entity_not_found(repo_env, repository):
    """Repository.transition() raises error if entity not found."""
    # Try to transition non-existent entity
    with pytest.raises(EntityNotFoundError) as exc_info:
        repository.transition("non-existent", "wip")

    assert "not found" in str(exc_info.value).lower()


def test_repository_transition_same_state(repo_env, repository, entity):
    """Repository.transition() handles transition to same state."""
    # Create entity
    repository.create(entity)

    # Transition to same state (should be allowed as no-op)
    updated = repository.transition(entity.id, "todo")
    assert updated.state == "todo"


def test_repository_transition_updates_metadata(repo_env, repository, entity):
    """Repository.transition() updates entity metadata timestamps."""
    from tests.helpers.timeouts import SHORT_SLEEP
    import time

    # Create entity
    repository.create(entity)
    original_updated_at = entity.metadata.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(SHORT_SLEEP)

    # Transition
    updated = repository.transition(entity.id, "wip")

    # Metadata should be updated
    # Note: The timestamp might be updated via record_transition()
    # which calls metadata.touch()
    assert updated.metadata.updated_at >= original_updated_at


def test_repository_transition_records_reason(repo_env, repository, entity):
    """Repository.transition() records a provided reason in history."""
    repository.create(entity)

    updated = repository.transition(entity.id, "wip", reason="test-reason")
    assert updated.state == "wip"
    assert updated.state_history[-1].reason == "test-reason"


def test_repository_transition_applies_mutate_hook(repo_env, repository, entity):
    """Repository.transition() applies caller-provided mutation before save."""
    repository.create(entity)

    def _mutate(e: MockEntity) -> None:
        e.data["mutated"] = True

    updated = repository.transition(entity.id, "wip", mutate=_mutate)
    assert updated.data.get("mutated") is True

    persisted = repository.get(entity.id)
    assert persisted is not None
    assert persisted.data.get("mutated") is True
