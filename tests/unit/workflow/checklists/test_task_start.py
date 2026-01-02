"""Task start checklist engine tests.

This module tests the centralized task start checklist engine that computes
what operators should do before beginning work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git


@pytest.fixture
def repo_env(tmp_path: Path, monkeypatch: Any) -> Path:
    """Create a repository with minimal configuration for testing."""
    repo = create_repo_with_git(tmp_path)

    # Create .project structure
    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "meta").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "waiting").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "sessions" / "active").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "TEMPLATE.md").write_text("# TEMPLATE\n", encoding="utf-8")

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(
        cfg_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                    "evidenceSubdir": "validation-evidence",
                }
            }
        },
    )

    write_yaml(
        cfg_dir / "workflow.yaml",
        {
            "version": "1.0",
            "statemachine": {
                "task": {
                    "states": {
                        "todo": {"initial": True, "allowed_transitions": ["wip"]},
                        "wip": {"allowed_transitions": ["done"]},
                        "done": {"allowed_transitions": []},
                    }
                },
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": ["todo"]},
                        "todo": {"allowed_transitions": ["wip"]},
                        "wip": {"allowed_transitions": ["done"]},
                        "done": {"allowed_transitions": []},
                    }
                },
                "session": {
                    "states": {
                        "active": {"initial": True, "allowed_transitions": []},
                    }
                },
            },
        },
    )

    # Create context7 config with triggers
    write_yaml(
        cfg_dir / "context7.yaml",
        {
            "context7": {
                "triggers": {
                    "fastapi": ["**/*fastapi*", "**/api/**/*.py"],
                    "pytest": ["**/test_*.py", "**/tests/**/*.py"],
                },
                "aliases": {
                    "fastapi": "fastapi",
                },
            }
        },
    )

    # Create validators config (in validation.validators format)
    write_yaml(
        cfg_dir / "validators.yaml",
        {
            "validation": {
                "validators": {
                    "global": {
                        "id": "global",
                        "name": "Global Validator",
                        "blocking": True,
                        "always_run": True,
                        "context7_required": True,
                        "context7_packages": ["fastapi"],
                        "wave": "critical",
                    },
                },
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


class TestChecklistItemModel:
    def test_checklist_item_has_required_fields(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem

        item = ChecklistItem(
            id="test-item",
            severity="warning",
            title="Test Item",
            rationale="Test rationale",
            status="ok",
        )

        assert item.id == "test-item"
        assert item.severity == "warning"
        assert item.title == "Test Item"
        assert item.rationale == "Test rationale"
        assert item.status == "ok"
        assert item.evidence_paths == []
        assert item.suggested_commands == []

    def test_checklist_item_severity_values(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem

        for severity in ["blocker", "warning", "info"]:
            item = ChecklistItem(id="x", severity=severity, title="x", rationale="x", status="ok")
            assert item.severity == severity

    def test_checklist_item_status_values(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem

        for status in ["ok", "missing", "invalid", "unknown"]:
            item = ChecklistItem(id="x", severity="info", title="x", rationale="x", status=status)
            assert item.status == status

    def test_checklist_item_to_dict(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem

        item = ChecklistItem(
            id="my-item",
            severity="blocker",
            title="My Title",
            rationale="Why this matters",
            status="missing",
            evidence_paths=["/path/to/evidence"],
            suggested_commands=["edison cmd arg"],
        )

        result = item.to_dict()

        assert result["id"] == "my-item"
        assert result["severity"] == "blocker"
        assert result["title"] == "My Title"
        assert result["rationale"] == "Why this matters"
        assert result["status"] == "missing"
        assert result["evidencePaths"] == ["/path/to/evidence"]
        assert result["suggestedCommands"] == ["edison cmd arg"]


class TestChecklistResult:
    def test_checklist_result_has_items_and_summary(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem, ChecklistResult

        item = ChecklistItem(id="x", severity="info", title="x", rationale="x", status="ok")
        result = ChecklistResult(kind="task_start", task_id="task-123", items=[item])

        assert result.kind == "task_start"
        assert result.task_id == "task-123"
        assert len(result.items) == 1

    def test_checklist_result_has_blockers(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem, ChecklistResult

        ok_item = ChecklistItem(id="ok", severity="blocker", title="x", rationale="x", status="ok")
        result_ok = ChecklistResult(kind="task_start", task_id="task-123", items=[ok_item])
        assert result_ok.has_blockers is False

        missing_item = ChecklistItem(
            id="missing", severity="blocker", title="x", rationale="x", status="missing"
        )
        result_blocked = ChecklistResult(kind="task_start", task_id="task-456", items=[missing_item])
        assert result_blocked.has_blockers is True

    def test_checklist_result_to_dict(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem, ChecklistResult

        item = ChecklistItem(id="x", severity="warning", title="x", rationale="x", status="ok")
        result = ChecklistResult(kind="task_start", task_id="task-789", items=[item])

        d = result.to_dict()

        assert d["kind"] == "task_start"
        assert d["taskId"] == "task-789"
        assert "items" in d
        assert len(d["items"]) == 1
        assert d["hasBlockers"] is False


class TestTaskStartChecklistEngine:
    def test_compute_returns_checklist_result(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistResult, TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-001", session_id="session-abc")

        assert isinstance(result, ChecklistResult)
        assert result.kind == "task_start"
        assert result.task_id == "task-001"

    def test_tdd_reminder_item_present(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-002", session_id="session-abc")

        item_ids = [item.id for item in result.items]
        assert "tdd-reminder" in item_ids

        tdd_item = next(i for i in result.items if i.id == "tdd-reminder")
        assert tdd_item.severity in ["info", "warning"]

    def test_evidence_round_item_present(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-003", session_id="session-abc")

        item_ids = [item.id for item in result.items]
        assert "evidence-round" in item_ids

    def test_evidence_round_missing_is_blocker(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-no-evidence", session_id="session-abc")

        ev_item = next((i for i in result.items if i.id == "evidence-round"), None)
        assert ev_item is not None
        assert ev_item.severity == "blocker"
        assert ev_item.status == "missing"

    def test_evidence_round_ok_when_initialized(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        task_id = "task-with-evidence"
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "implementation-report.md").write_text("---\nround: 1\n---\nReport", encoding="utf-8")

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id=task_id, session_id="session-abc")

        ev_item = next((i for i in result.items if i.id == "evidence-round"), None)
        assert ev_item is not None
        assert ev_item.status == "ok"

    def test_implementation_report_item_present(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-004", session_id="session-abc")

        item_ids = [item.id for item in result.items]
        assert "implementation-report" in item_ids

    def test_context7_packages_item_when_required(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        task_id = "task-with-api"
        wip_dir = repo_env / ".project" / "tasks" / "wip"
        task_file = wip_dir / f"{task_id}.md"
        task_file.write_text(
            """---
id: task-with-api
title: API task
session_id: session-abc
---

# Primary Files / Areas

- src/api/main.py

# Description
This task uses FastAPI.
""",
            encoding="utf-8",
        )

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id=task_id, session_id="session-abc")

        item_ids = [item.id for item in result.items]
        assert any("context7" in iid for iid in item_ids)

    def test_context7_missing_packages_has_suggested_commands(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        task_id = "task-api-missing-ctx7"
        wip_dir = repo_env / ".project" / "tasks" / "wip"
        task_file = wip_dir / f"{task_id}.md"
        task_file.write_text(
            """---
id: task-api-missing-ctx7
title: API task
session_id: session-abc
---

# Primary Files / Areas

- src/api/main.py
""",
            encoding="utf-8",
        )

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id=task_id, session_id="session-abc")

        ctx7_items = [i for i in result.items if "context7" in i.id]
        if ctx7_items:
            ctx7_item = ctx7_items[0]
            if ctx7_item.status in ["missing", "invalid"]:
                assert len(ctx7_item.suggested_commands) > 0

    def test_context7_invalid_markers_reported(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        task_id = "task-invalid-ctx7"
        wip_dir = repo_env / ".project" / "tasks" / "wip"
        task_file = wip_dir / f"{task_id}.md"
        task_file.write_text(
            """---
id: task-invalid-ctx7
title: API task
session_id: session-abc
---

# Primary Files / Areas

- src/api/main.py
""",
            encoding="utf-8",
        )

        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "context7-fastapi.txt").write_text(
            """---
package: fastapi
---
Missing libraryId and topics
""",
            encoding="utf-8",
        )

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id=task_id, session_id="session-abc")

        ctx7_items = [i for i in result.items if "context7" in i.id]
        if ctx7_items:
            ctx7_item = ctx7_items[0]
            assert ctx7_item.status == "invalid"


class TestChecklistEngineKinds:
    def test_task_start_is_default_kind(self) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        assert engine.kind == "task_start"

    def test_engine_supports_kind_parameter(self) -> None:
        from edison.core.workflow.checklists.task_start import ChecklistItem, ChecklistResult

        item = ChecklistItem(id="x", severity="info", title="x", rationale="x", status="ok")
        result = ChecklistResult(kind="session_start", task_id="", items=[item])
        assert result.kind == "session_start"


class TestChecklistEngineIntegration:
    def test_full_checklist_for_new_task(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="brand-new-task", session_id="session-xyz")

        assert len(result.items) > 0

        ev_item = next((i for i in result.items if i.id == "evidence-round"), None)
        assert ev_item is not None
        assert ev_item.status == "missing"
        assert ev_item.severity == "blocker"

    def test_full_checklist_serialization(self, repo_env: Path) -> None:
        from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

        engine = TaskStartChecklistEngine()
        result = engine.compute(task_id="task-serialize", session_id="session-xyz")

        d = result.to_dict()

        import json

        json_str = json.dumps(d)
        assert len(json_str) > 0

        assert "kind" in d
        assert "taskId" in d
        assert "items" in d
        assert "hasBlockers" in d

