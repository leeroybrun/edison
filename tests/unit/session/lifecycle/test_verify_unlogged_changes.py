"""Tests for detecting unlogged state/evidence changes in verify_session_health.

Task 005-tampering-protection-module: verify.py should detect changes to entity files
(task/QA/session) that are not paired with corresponding audit log entries.

This is tamper-EVIDENT (detect + report), not tamper-proof.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from edison.core.audit.logger import audit_event
from edison.core.config.domains.logging import LoggingConfig
from edison.core.session.lifecycle import verify as verify_mod
from edison.core.session.lifecycle.verify import verify_session_health
from edison.core.task import TaskRepository


class TestVerifyDetectsUnloggedChanges:
    """Test that verify_session_health detects unlogged state/evidence changes."""

    def test_detects_task_modification_without_audit_event(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Task file modified without corresponding audit log entry should be flagged.

        Scenario:
        1. Create a task via proper APIs (generates audit event)
        2. Directly modify the task file (simulating tampering)
        3. verify_session_health should detect the discrepancy
        """
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        # Create a session
        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        # Create a task via repository
        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="001-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,  # session_id is a direct attribute on Task
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Emit an audit event for the task creation (simulating proper API usage)
        import time
        audit_event(
            "task.create",
            repo_root=project_root,
            task_id="001-test-task",
            session_id=session_id,
        )

        # Delay to ensure file modification time is after audit event
        # Must be > 0.5s to exceed the tolerance in verify_entity_file
        time.sleep(1.5)

        # Directly modify the task file without going through APIs
        task_path = task_repo.get_path("001-test-task")
        original_content = task_path.read_text(encoding="utf-8")
        tampered_content = original_content.replace("Test Task", "Tampered Task")
        task_path.write_text(tampered_content, encoding="utf-8")

        # Mock session context to avoid worktree checks
        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        # Verify should detect the unlogged modification
        health = verify_session_health(session_id)

        # The health check should report unlogged changes
        assert "unloggedChanges" in health["categories"], (
            "verify_session_health should include 'unloggedChanges' category"
        )
        unlogged = health["categories"]["unloggedChanges"]
        assert len(unlogged) > 0, (
            "Should detect at least one unlogged change (the task modification)"
        )
        assert any(
            item.get("entityType") == "task" and item.get("entityId") == "001-test-task"
            for item in unlogged
        ), "Should identify the tampered task"

    def test_detects_qa_modification_without_audit_event(
        self, isolated_project_env: Path, monkeypatch
    ):
        """QA file modified without corresponding audit log entry should be flagged."""
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.qa.models import QARecord
        from edison.core.qa.workflow.repository import QARepository
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="002-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Create QA record
        qa_repo = QARepository(project_root=project_root)
        qa = QARecord(
            id="002-test-task-qa",
            task_id="002-test-task",
            state="waiting",
            title="QA for Test Task",
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        qa_repo.create(qa)

        # Emit audit events for the creation
        import time
        audit_event(
            "qa.create",
            repo_root=project_root,
            task_id="002-test-task",
            session_id=session_id,
        )

        # Delay to ensure file modification time is after audit event
        # Must be > 0.5s to exceed the tolerance in verify_entity_file
        time.sleep(1.5)

        # Directly modify the QA file without going through APIs
        qa_path = qa_repo.get_path("002-test-task-qa")
        original_content = qa_path.read_text(encoding="utf-8")
        tampered_content = original_content + "\n<!-- Tampered content -->\n"
        qa_path.write_text(tampered_content, encoding="utf-8")

        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        health = verify_session_health(session_id)

        assert "unloggedChanges" in health["categories"]
        unlogged = health["categories"]["unloggedChanges"]
        assert any(
            item.get("entityType") == "qa" and "002-test-task" in str(item.get("entityId", ""))
            for item in unlogged
        ), "Should identify the tampered QA record"

    def test_detects_evidence_modification_without_audit_event(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Evidence file modified without corresponding audit log entry should be flagged."""
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="003-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Create evidence file via proper method (should generate audit event)
        evidence_dir = project_root / ".project" / "qa" / "validation-reports" / "003-test-task" / "round-1"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = evidence_dir / "command-test.txt"
        evidence_file.write_text(
            "exitCode: 0\noutput: Original output\n",
            encoding="utf-8",
        )

        # Emit audit event for the evidence write
        import time
        audit_event(
            "evidence.write",
            repo_root=project_root,
            task_id="003-test-task",
            file=str(evidence_file.relative_to(project_root)),
        )

        # Delay to ensure file modification time is after audit event
        # Must be > 0.5s to exceed the tolerance in verify_entity_file
        time.sleep(1.5)

        # Tamper with evidence file directly
        evidence_file.write_text(
            "exitCode: 0\noutput: Tampered output\n",
            encoding="utf-8",
        )

        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        health = verify_session_health(session_id)

        assert "unloggedChanges" in health["categories"]
        unlogged = health["categories"]["unloggedChanges"]
        assert any(
            item.get("entityType") == "evidence" and "003-test-task" in str(item.get("file", ""))
            for item in unlogged
        ), "Should identify the tampered evidence file"

    def test_no_false_positives_for_properly_logged_changes(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Changes made through proper APIs with audit logging should not be flagged."""
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="004-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Emit audit event for the task creation (simulating proper API usage)
        # This is what makes it a "properly logged" change
        audit_event(
            "task.create",
            repo_root=project_root,
            task_id="004-test-task",
            session_id=session_id,
        )

        # Note: We don't transition here since guards may block it.
        # The test verifies that a properly created task (via APIs) is not flagged.

        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        health = verify_session_health(session_id)

        # Should NOT have unlogged changes for properly logged operations
        unlogged = health["categories"].get("unloggedChanges", [])
        assert not any(
            item.get("entityId") == "004-test-task"
            for item in unlogged
        ), "Properly logged changes should not be flagged as unlogged"

    def test_health_reports_discrepancies_with_actionable_output(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Health report should include actionable details for detected discrepancies."""
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="005-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Emit audit event for the task creation
        import time
        audit_event(
            "task.create",
            repo_root=project_root,
            task_id="005-test-task",
            session_id=session_id,
        )

        # Delay to ensure file modification time is after audit event
        # Must be > 0.5s to exceed the tolerance in verify_entity_file
        time.sleep(1.5)

        # Tamper with the task
        task_path = task_repo.get_path("005-test-task")
        original_content = task_path.read_text(encoding="utf-8")
        task_path.write_text(original_content + "\n<!-- Tampered -->\n", encoding="utf-8")

        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        health = verify_session_health(session_id)

        # Check that the report includes actionable details
        assert "unloggedChanges" in health["categories"]
        unlogged = health["categories"]["unloggedChanges"]

        # Find the tampered task entry
        task_entries = [
            item for item in unlogged
            if item.get("entityId") == "005-test-task"
        ]
        assert len(task_entries) > 0, "Should detect the tampered task"

        entry = task_entries[0]
        # Should include discrepancy details
        assert "filePath" in entry or "file" in entry, "Should include file path"
        assert "lastModified" in entry or "mtime" in entry, "Should include modification time"
        assert "lastAuditEvent" in entry or "expectedHash" in entry or "reason" in entry, (
            "Should include audit context or hash mismatch info"
        )

    def test_unlogged_changes_marks_health_not_ok(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Unlogged changes should cause health['ok'] to be False."""
        from edison.core.task.models import Task
        from edison.core.entity.base import EntityMetadata
        from edison.core.session.persistence.repository import SessionRepository

        project_root = isolated_project_env

        # Enable audit logging
        logging_config = (project_root / ".edison" / "config" / "logging.yaml")
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        session_id = "test-pid-12345-seq-1"
        session_repo = SessionRepository(project_root=project_root)
        from edison.core.session.core.models import Session
        session = Session.create(session_id=session_id, owner="test")
        session_repo.create(session)

        task_repo = TaskRepository(project_root=project_root)
        task = Task(
            id="006-test-task",
            title="Test Task",
            state="todo",
            session_id=session_id,
            metadata=EntityMetadata.create(session_id=session_id),
            state_history=[],
        )
        task_repo.create(task)

        # Emit audit event for the task creation
        import time
        audit_event(
            "task.create",
            repo_root=project_root,
            task_id="006-test-task",
            session_id=session_id,
        )

        # Delay to ensure file modification time is after audit event
        # Must be > 0.5s to exceed the tolerance in verify_entity_file
        time.sleep(1.5)

        # Tamper with the task
        task_path = task_repo.get_path("006-test-task")
        original_content = task_path.read_text(encoding="utf-8")
        task_path.write_text(original_content + "\n<!-- Tampered -->\n", encoding="utf-8")

        @contextmanager
        def _noop_in_session_worktree(_session_id: str):
            yield

        monkeypatch.setattr(
            verify_mod.SessionContext,
            "in_session_worktree",
            staticmethod(_noop_in_session_worktree),
        )
        monkeypatch.setattr(
            verify_mod.session_manager, "get_session", lambda _sid: {"id": _sid}
        )

        def _fake_next(_sid: str, scope: str = "session", limit: int = 0):
            return {"actions": [], "blockers": [], "reportsMissing": []}

        monkeypatch.setattr("edison.core.session.next.compute_next", _fake_next)

        health = verify_session_health(session_id)

        # Unlogged changes should make health not OK
        assert health["ok"] is False, (
            "Health should be not OK when unlogged changes are detected"
        )
