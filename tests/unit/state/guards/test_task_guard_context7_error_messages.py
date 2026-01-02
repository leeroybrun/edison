"""Tests for improved Context7 error messages in task guards.

TDD: RED phase - Tests for objective 1: improved error message content.

Context7 error messages must include:
1. `edison config show context7 --format yaml` command
2. `.edison/config/context7.yaml` path for configuration
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git


@pytest.fixture
def repo_with_context7(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a repository with Context7 configuration that will trigger errors."""
    repo = create_repo_with_git(tmp_path)

    # Create .project structure
    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "waiting").mkdir(parents=True, exist_ok=True)
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
                        "todo": "todo",
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

    # Create context7 config with triggers
    write_yaml(
        cfg_dir / "context7.yaml",
        {
            "context7": {
                "triggers": {
                    "fastapi": ["**/*fastapi*", "**/api/**/*.py"],
                    "pydantic": ["**/*pydantic*", "**/models/**/*.py"],
                },
                "aliases": {},
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


class TestContext7ErrorMessageContent:
    """Tests for Context7 error message improvements."""

    def test_context7_error_includes_config_show_command(
        self, repo_with_context7: Path
    ) -> None:
        """Error must include 'edison config show context7 --format yaml' command."""
        from edison.core.state.builtin.guards.task import can_finish_task

        task_id = "task-001"
        session_id = "test-session"

        # Create task with Primary Files that trigger Context7
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_with_context7 / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round with implementation report but no Context7 marker
        round_dir = (
            repo_with_context7
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
        )
        round_dir.mkdir(parents=True, exist_ok=True)

        impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_with_context7)}},
            "project_root": str(repo_with_context7),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)
        # Must include the config show command for viewing current configuration
        assert "edison config show context7" in error_msg
        assert "--format yaml" in error_msg or "yaml" in error_msg.lower()

    def test_context7_error_includes_config_file_path(
        self, repo_with_context7: Path
    ) -> None:
        """Error must include '.edison/config/context7.yaml' path."""
        from edison.core.state.builtin.guards.task import can_finish_task

        task_id = "task-002"
        session_id = "test-session"

        # Create task with Primary Files that trigger Context7
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_with_context7 / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        # Create evidence round with implementation report but no Context7 marker
        round_dir = (
            repo_with_context7
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
        )
        round_dir.mkdir(parents=True, exist_ok=True)

        impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_with_context7)}},
            "project_root": str(repo_with_context7),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)
        # Must include the config file path
        assert ".edison/config/context7.yaml" in error_msg

    def test_context7_error_actionable_message(
        self, repo_with_context7: Path
    ) -> None:
        """Error message should be actionable with clear instructions."""
        from edison.core.state.builtin.guards.task import can_finish_task

        task_id = "task-003"
        session_id = "test-session"

        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_with_context7 / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        round_dir = (
            repo_with_context7
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
        )
        round_dir.mkdir(parents=True, exist_ok=True)

        impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_with_context7)}},
            "project_root": str(repo_with_context7),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)

        # Error should provide actionable guidance:
        # 1. How to view current config
        assert "edison config show context7" in error_msg

        # 2. Where to modify config (to disable if needed)
        assert ".edison/config/context7.yaml" in error_msg

        # 3. How to save evidence (existing behavior)
        assert "edison evidence context7 save" in error_msg


class TestContext7ErrorMessageFormat:
    """Tests for the format and structure of Context7 error messages."""

    def test_error_message_format_multiline_readable(
        self, repo_with_context7: Path
    ) -> None:
        """Error message should be multi-line and human-readable."""
        from edison.core.state.builtin.guards.task import can_finish_task

        task_id = "task-004"
        session_id = "test-session"

        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
        (repo_with_context7 / ".project" / "tasks" / "wip" / f"{task_id}.md").write_text(
            task_content, encoding="utf-8"
        )

        round_dir = (
            repo_with_context7
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
        )
        round_dir.mkdir(parents=True, exist_ok=True)

        impl_content = """---
filesChanged:
  - src/api/main.py
---
"""
        (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

        ctx = {
            "task": {"id": task_id, "session_id": session_id},
            "session": {"id": session_id, "git": {"worktreePath": str(repo_with_context7)}},
            "project_root": str(repo_with_context7),
        }

        with pytest.raises(ValueError) as exc_info:
            can_finish_task(ctx)

        error_msg = str(exc_info.value)

        # Should be multi-line
        assert "\n" in error_msg

        # Should have distinct sections for diagnosis and fixing
        lines = error_msg.split("\n")
        assert len(lines) >= 5  # Header, evidence dir, missing markers, config info, fix commands
