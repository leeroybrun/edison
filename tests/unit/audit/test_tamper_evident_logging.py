"""Tests for tamper-evident logging of entity transitions and evidence writes.

These tests verify that the audit logging infrastructure captures all critical
state changes with immutable, append-only logs that can be used for forensics.

Following STRICT TDD - tests written FIRST, implementation second.
NO MOCKS - test real behavior only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


def _enable_tamper_evident_logging(repo: Path) -> None:
    """Enable tamper-evident logging for entity transitions and evidence writes."""
    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    "path": ".project/logs/edison/audit.jsonl",
                },
                # Enable tamper-evident logging for entities and evidence
                "tamperEvident": {
                    "enabled": True,
                    "entityTransitions": {"enabled": True},
                    "evidenceWrites": {"enabled": True},
                },
            }
        },
    )


def _create_task_state_machine_config(repo: Path) -> None:
    """Create minimal state machine config for task transitions.

    Uses `always_allow` guard to avoid guard failures in tests.
    This tests the audit logging, not the guard logic.
    """
    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        cfg_dir / "workflow.yaml",
        {
            "workflow": {
                "statemachine": {
                    "task": {
                        "states": {
                            "todo": {
                                "initial": True,
                                "allowed_transitions": [
                                    {"to": "wip", "guard": "always_allow"},
                                ],
                            },
                            "wip": {
                                "allowed_transitions": [
                                    {"to": "done", "guard": "always_allow"},
                                    {"to": "todo", "guard": "always_allow"},
                                ],
                            },
                            "done": {
                                "allowed_transitions": [
                                    {"to": "validated", "guard": "always_allow"},
                                ],
                            },
                            "validated": {"final": True, "allowed_transitions": []},
                        },
                    },
                    "qa": {
                        "states": {
                            "waiting": {
                                "initial": True,
                                "allowed_transitions": [
                                    {"to": "todo", "guard": "always_allow"},
                                ],
                            },
                            "todo": {
                                "allowed_transitions": [
                                    {"to": "wip", "guard": "always_allow"},
                                ],
                            },
                            "wip": {
                                "allowed_transitions": [
                                    {"to": "done", "guard": "always_allow"},
                                ],
                            },
                            "done": {
                                "allowed_transitions": [
                                    {"to": "validated", "guard": "always_allow"},
                                ],
                            },
                            "validated": {"final": True, "allowed_transitions": []},
                        }
                    },
                    "session": {
                        "states": {
                            "pending": {
                                "initial": True,
                                "allowed_transitions": [
                                    {"to": "active", "guard": "always_allow"},
                                    {"to": "done", "guard": "always_allow"},
                                ],
                            },
                            "active": {
                                "initial": True,
                                "allowed_transitions": [
                                    {"to": "done", "guard": "always_allow"},
                                ],
                            },
                            "done": {
                                "allowed_transitions": [
                                    {"to": "validated", "guard": "always_allow"},
                                ],
                            },
                            "validated": {"final": True, "allowed_transitions": []},
                        }
                    },
                },
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
                "session": {
                    "pending": "pending",
                    "active": "active",
                    "done": "done",
                    "validated": "validated",
                },
            },
        },
    )
    write_yaml(
        cfg_dir / "tasks.yaml",
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
    write_yaml(
        cfg_dir / "session.yaml",
        {
            "session": {
                "paths": {
                    "root": ".project/sessions",
                },
            }
        },
    )


def _get_audit_events(repo: Path) -> list[dict]:
    """Read and parse all audit events from the JSONL log."""
    log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
    if not log_path.exists():
        return []
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


# =============================================================================
# Entity Transition Logging Tests
# =============================================================================


class TestEntityTransitionLogging:
    """Tests for logging entity state transitions."""

    def test_task_transition_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """Task state transitions emit audit events with old/new state."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-001", title="Test Task")
        task_repo.create(task)

        # Transition from todo -> wip
        task_repo.transition("T-001", "wip")

        events = _get_audit_events(repo)
        transition_events = [e for e in events if e.get("event") == "entity.transition"]

        assert len(transition_events) >= 1, "Expected at least one entity.transition event"
        ev = transition_events[-1]
        assert ev.get("entity_type") == "task"
        assert ev.get("entity_id") == "T-001"
        assert ev.get("from_state") == "todo"
        assert ev.get("to_state") == "wip"
        assert ev.get("ts") is not None

    def test_qa_transition_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """QA state transitions emit audit events."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository
        from edison.core.qa.models import QARecord
        from edison.core.qa.workflow.repository import QARepository

        # Create task first
        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-002", title="Test Task with QA")
        task_repo.create(task)

        # Create QA record
        qa_repo = QARepository(project_root=repo)
        qa = QARecord.create("T-002-qa", task_id="T-002", title="QA for T-002")
        qa_repo.create(qa)

        # Transition QA from waiting -> todo
        qa_repo.transition("T-002-qa", "todo")

        events = _get_audit_events(repo)
        transition_events = [e for e in events if e.get("event") == "entity.transition"]

        # Find the QA transition event
        qa_transitions = [e for e in transition_events if e.get("entity_type") == "qa"]
        assert len(qa_transitions) >= 1, "Expected at least one qa entity.transition event"
        ev = qa_transitions[-1]
        assert ev.get("entity_id") == "T-002-qa"
        assert ev.get("from_state") == "waiting"
        assert ev.get("to_state") == "todo"

    def test_session_transition_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """Session state transitions emit audit events."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.config.domains import SessionConfig
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        session_cfg = SessionConfig(repo_root=repo)
        initial_state = session_cfg.get_initial_session_state()

        session_repo = SessionRepository(project_root=repo)
        session = Session.create("sess-001", owner="tester", state=initial_state)
        session_repo.create(session)

        # Transition from initial state -> done (using always_allow guard)
        session_repo.transition("sess-001", "done")

        events = _get_audit_events(repo)
        transition_events = [e for e in events if e.get("event") == "entity.transition"]

        session_transitions = [e for e in transition_events if e.get("entity_type") == "session"]
        assert len(session_transitions) >= 1, "Expected at least one session entity.transition event"
        ev = session_transitions[-1]
        assert ev.get("entity_id") == "sess-001"
        assert ev.get("from_state") == initial_state
        assert ev.get("to_state") == "done"

    def test_transition_event_includes_context_ids(self, tmp_path: Path, monkeypatch) -> None:
        """Transition events include session and invocation context when available."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        monkeypatch.setenv("AGENTS_SESSION", "sess-context-test")
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        # Create session first
        from edison.core.session.core.models import Session
        from edison.core.session.persistence.repository import SessionRepository

        session_repo = SessionRepository(project_root=repo)
        session = Session.create("sess-context-test", owner="tester", state="active")
        session_repo.create(session)

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-003", title="Context Test Task", session_id="sess-context-test")
        task_repo.create(task)

        task_repo.transition("T-003", "wip")

        events = _get_audit_events(repo)
        transition_events = [e for e in events if e.get("event") == "entity.transition"]
        ev = transition_events[-1]

        # Session ID should be included
        assert ev.get("session_id") == "sess-context-test"

    def test_transition_logging_disabled_emits_no_events(self, tmp_path: Path, monkeypatch) -> None:
        """When tamper-evident logging is disabled, no events are emitted."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _create_task_state_machine_config(repo)

        # Disable tamper-evident logging
        cfg_dir = repo / ".edison" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        write_yaml(
            cfg_dir / "logging.yaml",
            {
                "logging": {
                    "enabled": True,
                    "audit": {"enabled": True, "path": ".project/logs/edison/audit.jsonl"},
                    "tamperEvident": {
                        "enabled": False,
                    },
                }
            },
        )
        reset_edison_caches()

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-004", title="No Logging Task")
        task_repo.create(task)
        task_repo.transition("T-004", "wip")

        events = _get_audit_events(repo)
        transition_events = [e for e in events if e.get("event") == "entity.transition"]
        assert len(transition_events) == 0, "Expected no entity.transition events when disabled"


# =============================================================================
# Evidence Write Logging Tests
# =============================================================================


class TestEvidenceWriteLogging:
    """Tests for logging evidence write operations."""

    def test_bundle_write_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """Writing a bundle summary emits an audit event."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id="T-100", project_root=repo)
        svc.ensure_round()

        bundle_data = {"status": "approved", "files": ["file1.py"]}
        svc.write_bundle(bundle_data)

        events = _get_audit_events(repo)
        write_events = [e for e in events if e.get("event") == "evidence.write"]

        assert len(write_events) >= 1, "Expected at least one evidence.write event"
        ev = write_events[-1]
        assert ev.get("task_id") == "T-100"
        assert ev.get("artifact_type") == "bundle"
        assert ev.get("round") == 1
        assert ev.get("ts") is not None

    def test_implementation_report_write_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """Writing an implementation report emits an audit event."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id="T-101", project_root=repo)
        svc.ensure_round()

        report_data = {"summary": "Implementation complete", "files_changed": 5}
        svc.write_implementation_report(report_data)

        events = _get_audit_events(repo)
        write_events = [e for e in events if e.get("event") == "evidence.write"]

        impl_events = [e for e in write_events if e.get("artifact_type") == "implementation_report"]
        assert len(impl_events) >= 1, "Expected at least one implementation_report evidence.write event"
        ev = impl_events[-1]
        assert ev.get("task_id") == "T-101"
        assert ev.get("round") == 1

    def test_validator_report_write_emits_audit_event(self, tmp_path: Path, monkeypatch) -> None:
        """Writing a validator report emits an audit event."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id="T-102", project_root=repo)
        svc.ensure_round()

        validator_data = {"verdict": "pass", "findings": []}
        svc.write_validator_report("validator-security", validator_data)

        events = _get_audit_events(repo)
        write_events = [e for e in events if e.get("event") == "evidence.write"]

        validator_events = [e for e in write_events if e.get("artifact_type") == "validator_report"]
        assert len(validator_events) >= 1, "Expected at least one validator_report evidence.write event"
        ev = validator_events[-1]
        assert ev.get("task_id") == "T-102"
        assert ev.get("validator_id") == "validator-security"
        assert ev.get("round") == 1

    def test_evidence_write_includes_file_path(self, tmp_path: Path, monkeypatch) -> None:
        """Evidence write events include the file path for forensics."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id="T-103", project_root=repo)
        svc.ensure_round()

        svc.write_bundle({"status": "pending"})

        events = _get_audit_events(repo)
        write_events = [e for e in events if e.get("event") == "evidence.write"]
        ev = write_events[-1]

        assert ev.get("path") is not None
        assert "T-103" in ev.get("path", "")
        assert "round-1" in ev.get("path", "")

    def test_evidence_logging_disabled_emits_no_events(self, tmp_path: Path, monkeypatch) -> None:
        """When evidence write logging is disabled, no events are emitted."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _create_task_state_machine_config(repo)

        cfg_dir = repo / ".edison" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        write_yaml(
            cfg_dir / "logging.yaml",
            {
                "logging": {
                    "enabled": True,
                    "audit": {"enabled": True, "path": ".project/logs/edison/audit.jsonl"},
                    "tamperEvident": {
                        "enabled": True,
                        "evidenceWrites": {"enabled": False},
                    },
                }
            },
        )
        reset_edison_caches()

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id="T-104", project_root=repo)
        svc.ensure_round()
        svc.write_bundle({"status": "test"})

        events = _get_audit_events(repo)
        write_events = [e for e in events if e.get("event") == "evidence.write"]
        assert len(write_events) == 0, "Expected no evidence.write events when disabled"


# =============================================================================
# Append-Only Semantics Tests
# =============================================================================


class TestAppendOnlySemantics:
    """Tests verifying append-only behavior for tamper evidence."""

    def test_multiple_transitions_appended_in_order(self, tmp_path: Path, monkeypatch) -> None:
        """Multiple transitions are all appended in chronological order."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-200", title="Multi Transition Task")
        task_repo.create(task)

        # Multiple transitions
        task_repo.transition("T-200", "wip")
        task_repo.transition("T-200", "done")

        events = _get_audit_events(repo)
        transitions = [e for e in events if e.get("event") == "entity.transition" and e.get("entity_id") == "T-200"]

        assert len(transitions) == 2, "Expected 2 transition events"
        assert transitions[0].get("from_state") == "todo"
        assert transitions[0].get("to_state") == "wip"
        assert transitions[1].get("from_state") == "wip"
        assert transitions[1].get("to_state") == "done"

    def test_log_file_is_append_only_jsonl(self, tmp_path: Path, monkeypatch) -> None:
        """The audit log is valid JSONL format (one JSON object per line)."""
        repo = create_repo_with_git(tmp_path, name="repo")
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        _enable_tamper_evident_logging(repo)
        _create_task_state_machine_config(repo)
        reset_edison_caches()

        from edison.core.task.models import Task
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=repo)
        task = Task.create("T-201", title="JSONL Test")
        task_repo.create(task)
        task_repo.transition("T-201", "wip")

        log_path = repo / ".project" / "logs" / "edison" / "audit.jsonl"
        assert log_path.exists()

        lines = log_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.strip():
                # Each line should be valid JSON
                parsed = json.loads(line)
                assert isinstance(parsed, dict)
                assert "ts" in parsed
                assert "event" in parsed
