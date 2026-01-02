"""Context7 early enforcement tests for session next.

Tests for surfacing Context7 requirements early (during wip status) via session next.

TDD: RED phase - Write failing tests first.
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
    """Create a repository with Context7 config and validation setup."""
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
                    },
                    "semantic_states": {
                        "wip": "wip",
                        "done": "done",
                    },
                },
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": ["todo"]},
                        "todo": {"allowed_transitions": ["wip"]},
                        "wip": {"allowed_transitions": ["done"]},
                        "done": {"allowed_transitions": []},
                    },
                    "semantic_states": {
                        "wip": "wip",
                        "todo": "todo",
                    },
                },
                "session": {
                    "states": {
                        "active": {"initial": True, "allowed_transitions": []},
                    }
                },
            },
        },
    )

    # Create context7 config
    write_yaml(
        cfg_dir / "context7.yaml",
        {
            "context7": {
                "triggers": {
                    "fastapi": ["**/*fastapi*", "**/api/**/*.py"],
                    "pytest": ["**/test_*.py"],
                },
                "aliases": {},
            }
        },
    )

    # Create validation config with context7 requirements
    # Using always_run: true to ensure validator triggers without needing actual file changes
    write_yaml(
        cfg_dir / "validation.yaml",
        {
            "validation": {
                "validators": {
                    "api-validator": {
                        "name": "API Validator",
                        "engine": "delegation",
                        "wave": "critical",
                        "blocking": True,
                        "always_run": True,
                        "triggers": [],
                        "context7_required": True,
                        "context7_packages": ["fastapi"],
                    }
                }
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


class TestSessionNextContext7EarlyEnforcement:
    """Tests for surfacing Context7 requirements early via session next."""

    def test_session_next_reports_context7_for_wip_tasks(self, repo_env: Path) -> None:
        """session next should report Context7 requirements for tasks in wip status."""
        from edison.core.session.next.actions import build_reports_missing

        session_id = "test-session-1"
        task_id = "task-001"

        # Create task in wip state
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_env / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create QA in waiting (task not yet done)
        qa_content = f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA {task_id}"
round: 1
---

# QA {task_id}
"""
        (repo_env / ".project" / "qa" / "waiting" / f"{task_id}-qa.md").write_text(
            qa_content, encoding="utf-8"
        )

        # Create evidence round directory
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Create implementation report
        impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        missing = build_reports_missing({"id": session_id})

        # Should have context7 entry for wip task
        ctx7_entries = [
            e for e in missing
            if e.get("type") == "context7" and e.get("taskId") == task_id
        ]
        assert ctx7_entries, "Expected Context7 entry for wip task"

    def test_session_next_context7_distinguishes_missing_vs_invalid(self, repo_env: Path) -> None:
        """session next should distinguish missing from invalid Context7 markers."""
        from edison.core.session.next.actions import build_context7_status

        session_id = "test-session-2"
        task_id = "task-002"

        # Create task in wip state
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_env / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid marker (missing required fields)
        invalid_marker = """---
package: fastapi
---
Missing libraryId and topics.
"""
        (round_dir / "context7-fastapi.txt").write_text(invalid_marker, encoding="utf-8")

        result = build_context7_status(task_id, session_id)

        assert "invalid" in result
        assert any(p["package"] == "fastapi" for p in result["invalid"])
        assert "missing_fields" in result["invalid"][0]

    def test_session_next_context7_shows_evidence_directory(self, repo_env: Path) -> None:
        """session next Context7 status should include the evidence directory path."""
        from edison.core.session.next.actions import build_context7_status

        session_id = "test-session-3"
        task_id = "task-003"

        # Create task
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation
"""
        (repo_env / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        result = build_context7_status(task_id, session_id)

        assert "evidence_dir" in result
        assert str(round_dir) in result["evidence_dir"]

    def test_session_next_context7_includes_suggested_commands(self, repo_env: Path) -> None:
        """session next should include suggested commands for fixing Context7 issues."""
        from edison.core.session.next.actions import build_context7_status

        session_id = "test-session-4"
        task_id = "task-004"

        # Create task
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_env / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round but no markers
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        result = build_context7_status(task_id, session_id)

        assert "suggested_commands" in result
        # Should include template command
        assert any("template" in cmd for cmd in result["suggested_commands"])


class TestTaskGuardContext7ErrorMessages:
    """Tests for improved Context7 error messages in task guard."""

    def test_can_finish_task_error_shows_invalid_markers(self, repo_env: Path) -> None:
        """can_finish_task should show invalid markers separately from missing."""
        from edison.core.state.builtin.guards.task import can_finish_task

        session_id = "test-session-5"
        task_id = "task-005"

        # Create task in done state (for finishing)
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_env / ".project" / "tasks" / "done" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Create implementation report
        impl_content = """---
filesChanged:
  - src/api/main.py
---
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        # Write invalid marker
        invalid_marker = """---
package: fastapi
---
"""
        (round_dir / "context7-fastapi.txt").write_text(invalid_marker, encoding="utf-8")

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_env)}},
            "project_root": str(repo_env),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)
        # Should mention invalid (not just missing)
        assert "invalid" in error_msg.lower() or "missing_fields" in error_msg.lower()

    def test_can_finish_task_error_shows_evidence_directory(self, repo_env: Path) -> None:
        """can_finish_task error should include the evidence directory path."""
        from edison.core.state.builtin.guards.task import can_finish_task

        session_id = "test-session-6"
        task_id = "task-006"

        # Create task
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_env / ".project" / "tasks" / "done" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round
        round_dir = repo_env / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Create implementation report
        impl_content = """---
filesChanged:
  - src/api/main.py
---
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        # No context7 marker - should be missing

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_env)}},
            "project_root": str(repo_env),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)
        # Should include evidence directory path
        assert "round-1" in error_msg or "validation-evidence" in error_msg


class TestOutputFormatting:
    """Tests for Context7 status formatting in session next output."""

    def test_format_human_readable_shows_context7_missing_vs_invalid(self, repo_env: Path) -> None:
        """Human readable output should distinguish missing from invalid markers."""
        from edison.core.session.next.output import format_human_readable

        payload = {
            "sessionId": "test-session",
            "actions": [],
            "reportsMissing": [
                {
                    "taskId": "task-007",
                    "type": "context7",
                    "packages": ["pydantic"],  # missing
                    "invalidMarkers": [
                        {
                            "package": "fastapi",
                            "missing_fields": ["libraryId", "topics"],
                        }
                    ],
                    "evidenceDir": "/path/to/round-1",
                    "suggested": [
                        "edison evidence context7 template fastapi",
                        "edison evidence context7 save task-007 fastapi --library-id /tiangolo/fastapi",
                    ],
                }
            ],
        }

        output = format_human_readable(payload)

        # Should mention missing packages
        assert "pydantic" in output.lower() or "missing" in output.lower()
        # Should mention invalid packages
        assert "fastapi" in output.lower() or "invalid" in output.lower()
        # Should show evidence directory
        assert "round-1" in output or "evidence" in output.lower()
