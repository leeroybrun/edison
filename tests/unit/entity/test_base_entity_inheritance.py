"""Tests for BaseEntity inheritance in Task, QARecord, and Session.

These tests verify that entity models correctly use the shared
record_transition implementation from BaseEntity, eliminating
code duplication (DRY principle).
"""
import pytest

from edison.core.entity import EntityMetadata, StateHistoryEntry
from edison.core.entity.base import record_transition_impl


class TestRecordTransitionImpl:
    """Tests for the shared record_transition_impl function."""

    def test_appends_history_entry(self):
        """Verify that record_transition_impl appends to state_history."""
        # Create a mock entity-like object
        class MockEntity:
            def __init__(self):
                self.state_history = []
                self.metadata = EntityMetadata.create()

        entity = MockEntity()
        
        record_transition_impl(entity, "todo", "wip", reason="starting work")
        
        assert len(entity.state_history) == 1
        entry = entity.state_history[0]
        assert entry.from_state == "todo"
        assert entry.to_state == "wip"
        assert entry.reason == "starting work"

    def test_updates_metadata_timestamp(self):
        """Verify that record_transition_impl calls metadata.touch()."""
        class MockEntity:
            def __init__(self):
                self.state_history = []
                self.metadata = EntityMetadata.create()

        entity = MockEntity()
        original_updated_at = entity.metadata.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        record_transition_impl(entity, "todo", "wip")
        
        # Metadata should be touched (updated_at changed)
        assert entity.metadata.updated_at >= original_updated_at

    def test_records_violations(self):
        """Verify that violations are recorded in the history entry."""
        class MockEntity:
            def __init__(self):
                self.state_history = []
                self.metadata = EntityMetadata.create()

        entity = MockEntity()
        violations = ["RULE.001", "RULE.002"]
        
        record_transition_impl(entity, "wip", "done", violations=violations)
        
        entry = entity.state_history[0]
        assert entry.violations == violations

    def test_multiple_transitions(self):
        """Verify that multiple transitions are properly tracked."""
        class MockEntity:
            def __init__(self):
                self.state_history = []
                self.metadata = EntityMetadata.create()

        entity = MockEntity()
        
        record_transition_impl(entity, "todo", "wip")
        record_transition_impl(entity, "wip", "blocked", reason="waiting on dependency")
        record_transition_impl(entity, "blocked", "wip")
        record_transition_impl(entity, "wip", "done")
        
        assert len(entity.state_history) == 4
        assert entity.state_history[0].to_state == "wip"
        assert entity.state_history[1].to_state == "blocked"
        assert entity.state_history[2].to_state == "wip"
        assert entity.state_history[3].to_state == "done"


class TestTaskRecordTransition:
    """Tests for Task.record_transition using shared implementation."""

    def test_task_record_transition_delegates_to_impl(self):
        """Verify Task.record_transition works correctly."""
        from edison.core.task.models import Task
        
        task = Task.create("TASK-001", "Test task")
        
        task.record_transition("todo", "wip", reason="claimed")
        
        assert len(task.state_history) == 1
        assert task.state_history[0].from_state == "todo"
        assert task.state_history[0].to_state == "wip"
        assert task.state_history[0].reason == "claimed"

    def test_task_record_transition_with_violations(self):
        """Verify Task records violations correctly."""
        from edison.core.task.models import Task
        
        task = Task.create("TASK-002", "Test task with violations")
        violations = ["RULE.TDD.001"]
        
        task.record_transition("wip", "done", violations=violations)
        
        assert task.state_history[0].violations == violations


class TestQARecordRecordTransition:
    """Tests for QARecord.record_transition using shared implementation."""

    def test_qa_record_transition_delegates_to_impl(self):
        """Verify QARecord.record_transition works correctly."""
        from edison.core.qa.models import QARecord
        
        qa = QARecord.create("QA-001", "TASK-001", "Test QA")
        
        qa.record_transition("waiting", "todo", reason="ready for review")
        
        assert len(qa.state_history) == 1
        assert qa.state_history[0].from_state == "waiting"
        assert qa.state_history[0].to_state == "todo"

    def test_qa_record_transition_with_violations(self):
        """Verify QARecord records violations correctly."""
        from edison.core.qa.models import QARecord
        
        qa = QARecord.create("QA-002", "TASK-002", "Test QA")
        violations = ["RULE.QA.001"]
        
        qa.record_transition("todo", "wip", violations=violations)
        
        assert qa.state_history[0].violations == violations


class TestSessionRecordTransition:
    """Tests for Session.record_transition using shared implementation."""

    def test_session_record_transition_delegates_to_impl(self):
        """Verify Session.record_transition works correctly."""
        from edison.core.session.core.models import Session
        
        session = Session.create("SESSION-001")
        
        session.record_transition("pending", "active", reason="started")
        
        assert len(session.state_history) == 1
        assert session.state_history[0].from_state == "pending"
        assert session.state_history[0].to_state == "active"

    def test_session_record_transition_with_violations(self):
        """Verify Session records violations correctly."""
        from edison.core.session.core.models import Session
        
        session = Session.create("SESSION-002")
        violations = ["RULE.SESSION.001"]
        
        session.record_transition("active", "closing", violations=violations)
        
        assert session.state_history[0].violations == violations


class TestEntityConsistency:
    """Tests to verify all entities use the same record_transition behavior."""

    def test_all_entities_produce_consistent_history_format(self):
        """Verify all entity types produce identical history entry structure."""
        from edison.core.task.models import Task
        from edison.core.qa.models import QARecord
        from edison.core.session.core.models import Session
        
        task = Task.create("TASK-001", "Test")
        qa = QARecord.create("QA-001", "TASK-001", "Test QA")
        session = Session.create("SESSION-001")
        
        # Record same transition on all
        reason = "test reason"
        violations = ["RULE.001"]
        
        task.record_transition("from", "to", reason=reason, violations=violations)
        qa.record_transition("from", "to", reason=reason, violations=violations)
        session.record_transition("from", "to", reason=reason, violations=violations)
        
        # All should have identical structure
        task_entry = task.state_history[0]
        qa_entry = qa.state_history[0]
        session_entry = session.state_history[0]
        
        # Same fields
        assert task_entry.from_state == qa_entry.from_state == session_entry.from_state
        assert task_entry.to_state == qa_entry.to_state == session_entry.to_state
        assert task_entry.reason == qa_entry.reason == session_entry.reason
        assert task_entry.violations == qa_entry.violations == session_entry.violations
        
        # All have timestamps
        assert task_entry.timestamp
        assert qa_entry.timestamp
        assert session_entry.timestamp






