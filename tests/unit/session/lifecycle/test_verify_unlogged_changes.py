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


class TestVerifyHandlesSymlinkedProject:
    """Test that verification correctly handles symlinked .project/ directories.

    In Edison's meta-worktree layout, `.project/` is often a symlink to an external
    `_meta` directory. The verification code must handle this case without raising
    ValueError when calling relative_to() after symlink resolution.
    """

    def test_symlinked_project_dir_does_not_raise_value_error(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Verification should handle symlinked .project/ without ValueError.

        Scenario:
        1. Create a project with a symlinked .project/ directory
        2. Create entity files under the symlinked directory
        3. verify_entity_file should not raise ValueError when resolving paths
        """
        from edison.core.audit.verification import verify_entity_file, read_audit_log

        project_root = isolated_project_env

        # Create an external directory to simulate _meta worktree
        external_meta = project_root.parent / "_meta_external"
        external_meta.mkdir(parents=True, exist_ok=True)

        # Create sessions directory in the external location
        sessions_dir = external_meta / "sessions" / "wip" / "test-session" / "tasks" / "todo"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create a task file in the external directory
        task_file = sessions_dir / "001-test-task.md"
        task_file.write_text(
            "---\nid: 001-test-task\ntitle: Test Task\nstate: todo\n---\n# Test Task\n",
            encoding="utf-8",
        )

        # Create symlink .project -> external_meta
        project_dir = project_root / ".project"
        if project_dir.exists():
            # Remove existing .project (created by fixture)
            import shutil
            if project_dir.is_symlink():
                project_dir.unlink()
            else:
                shutil.rmtree(project_dir)
        project_dir.symlink_to(external_meta)

        # Enable audit logging
        logging_config = project_root / ".edison" / "config" / "logging.yaml"
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        # Create audit log with a dummy event
        audit_dir = external_meta / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log = audit_dir / "audit.jsonl"
        import time
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        audit_log.write_text(
            f'{{"event": "task.create", "task_id": "001-test-task", "ts": "{ts}"}}\n',
            encoding="utf-8",
        )

        # Simulate that task was modified AFTER the audit event
        time.sleep(1.5)
        task_file.write_text(
            "---\nid: 001-test-task\ntitle: Tampered Task\nstate: todo\n---\n# Tampered\n",
            encoding="utf-8",
        )

        # Get the task path through the symlink
        task_path_via_symlink = project_root / ".project" / "sessions" / "wip" / "test-session" / "tasks" / "todo" / "001-test-task.md"

        # Read audit log
        audit_events = read_audit_log(project_root)
        assert len(audit_events) > 0, "Should have audit events"

        # This should NOT raise ValueError even though the file is in a symlinked directory
        # that resolves outside project_root
        try:
            result = verify_entity_file(
                project_root=project_root,
                entity_type="task",
                entity_id="001-test-task",
                file_path=task_path_via_symlink,
                audit_events=audit_events,
            )
            # If we get here, no exception was raised - good!
            # The result should be an UnloggedChange since we tampered
            assert result is not None, (
                "Should detect the unlogged change even with symlinked directory"
            )
            assert result.entity_id == "001-test-task"
            assert "Task" in result.file_path or "001-test-task" in result.file_path.lower() or ".project" in result.file_path, (
                f"File path should be meaningful, got: {result.file_path}"
            )
        except ValueError as e:
            # This is the bug we're fixing - should not happen
            pytest.fail(
                f"verify_entity_file raised ValueError with symlinked .project/: {e}"
            )

    def test_symlinked_evidence_dir_does_not_raise_value_error(
        self, isolated_project_env: Path, monkeypatch
    ):
        """Evidence verification should handle symlinked .project/ without ValueError."""
        from edison.core.audit.verification import verify_entity_file, read_audit_log

        project_root = isolated_project_env

        # Create an external directory to simulate _meta worktree
        external_meta = project_root.parent / "_meta_external_evidence"
        external_meta.mkdir(parents=True, exist_ok=True)

        # Create evidence directory in the external location
        evidence_dir = external_meta / "qa" / "validation-reports" / "001-test-task" / "round-1"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Create an evidence file
        evidence_file = evidence_dir / "test-output.txt"
        evidence_file.write_text("exitCode: 0\noutput: Original output\n", encoding="utf-8")

        # Create symlink .project -> external_meta
        project_dir = project_root / ".project"
        if project_dir.exists():
            import shutil
            if project_dir.is_symlink():
                project_dir.unlink()
            else:
                shutil.rmtree(project_dir)
        project_dir.symlink_to(external_meta)

        # Enable audit logging
        logging_config = project_root / ".edison" / "config" / "logging.yaml"
        logging_config.parent.mkdir(parents=True, exist_ok=True)
        logging_config.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  audit:\n"
            "    enabled: true\n"
            "    path: .project/audit/audit.jsonl\n",
            encoding="utf-8",
        )

        # Create audit log with an evidence write event
        audit_dir = external_meta / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log = audit_dir / "audit.jsonl"
        import time
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        audit_log.write_text(
            f'{{"event": "evidence.write", "task_id": "001-test-task", "file": ".project/qa/validation-reports/001-test-task/round-1/test-output.txt", "ts": "{ts}"}}\n',
            encoding="utf-8",
        )

        # Simulate that evidence was modified AFTER the audit event
        time.sleep(1.5)
        evidence_file.write_text("exitCode: 0\noutput: Tampered output\n", encoding="utf-8")

        # Get the evidence path through the symlink
        evidence_path_via_symlink = project_root / ".project" / "qa" / "validation-reports" / "001-test-task" / "round-1" / "test-output.txt"

        # Read audit log
        audit_events = read_audit_log(project_root)
        assert len(audit_events) > 0, "Should have audit events"

        # This should NOT raise ValueError
        try:
            result = verify_entity_file(
                project_root=project_root,
                entity_type="evidence",
                entity_id="001-test-task",
                file_path=evidence_path_via_symlink,
                audit_events=audit_events,
            )
            # If we get here, no exception was raised - good!
            # The result should be an UnloggedChange since we tampered
            assert result is not None, (
                "Should detect the unlogged change even with symlinked directory"
            )
            assert "test-output" in result.file_path.lower() or ".project" in result.file_path, (
                f"File path should be meaningful, got: {result.file_path}"
            )
        except ValueError as e:
            pytest.fail(
                f"verify_entity_file raised ValueError with symlinked .project/: {e}"
            )
