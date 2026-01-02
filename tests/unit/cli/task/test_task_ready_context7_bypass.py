"""Tests for Context7 bypass flag in task ready command.

TDD: RED phase - Tests for objective 2: explicit bypass flag.

The --skip-context7 flag must:
1. Only bypass Context7 checks (not all guards)
2. Print a loud warning
3. Leave an audit trace in the implementation report / audit log
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from edison.core.qa.evidence.command_evidence import write_command_evidence
from helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_all_and_reload
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git


@pytest.fixture
def repo_with_context7_trigger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a repository with Context7 configuration that will trigger a block."""
    repo = create_repo_with_git(tmp_path)

    # Create .project structure
    (repo / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "wip").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "tasks" / "done").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "waiting").mkdir(parents=True, exist_ok=True)
    (repo / ".project" / "qa" / "todo").mkdir(parents=True, exist_ok=True)
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
                        "waiting": "waiting",
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
                },
                "aliases": {},
            }
        },
    )

    setup_project_root(monkeypatch, repo)
    reset_all_and_reload()
    return repo


def _create_test_session(repo: Path, session_id: str) -> None:
    """Create a test session using the nested layout (session.json inside directory)."""
    import json

    session_dir = repo / ".project" / "sessions" / "wip" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    session_data = {
        "id": session_id,
        "state": "wip",
    }
    (session_dir / "session.json").write_text(json.dumps(session_data), encoding="utf-8")


def _create_wip_task_with_context7_trigger(
    repo: Path, task_id: str, session_id: str
) -> Path:
    """Create a wip task that triggers Context7 requirements."""
    task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation

## Primary Files / Areas
- src/api/main.py
"""
    task_path = repo / ".project" / "tasks" / "wip" / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(task_content, encoding="utf-8")

    # Create QA in waiting
    qa_content = f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA {task_id}"
session_id: "{session_id}"
round: 1
---

# QA {task_id}
"""
    qa_path = repo / ".project" / "qa" / "waiting" / f"{task_id}-qa.md"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(qa_content, encoding="utf-8")

    # Create evidence round with implementation report (but no Context7 marker)
    round_dir = repo / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)

    impl_content = """---
filesChanged:
  - src/api/main.py
---
Implementation report.
"""
    (round_dir / "implementation-report.md").write_text(impl_content, encoding="utf-8")

    # Create command evidence files (passing exit codes) in v1 format
    # These are required by the evidence validator, separate from Context7
    now = datetime.now(timezone.utc)
    for cmd_name in ["type-check", "lint", "test", "build"]:
        write_command_evidence(
            path=round_dir / f"command-{cmd_name}.txt",
            task_id=task_id,
            round_num=1,
            command_name=cmd_name,
            command=f"pnpm {cmd_name}",
            cwd=str(repo),
            exit_code=0,
            output=f"Command output for {cmd_name}.\n",
            started_at=now,
            completed_at=now,
            shell="bash",
            pipefail=True,
        )

    return task_path


class TestBypassFlagRegistration:
    """Tests for --skip-context7 flag registration in CLI."""

    def test_task_ready_has_skip_context7_flag(self) -> None:
        """task ready command should accept --skip-context7 flag."""
        from edison.cli.task.ready import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        # Should not raise when parsing --skip-context7
        args = parser.parse_args(["task-001", "--skip-context7"])
        assert hasattr(args, "skip_context7")
        assert args.skip_context7 is True

    def test_task_ready_skip_context7_default_false(self) -> None:
        """--skip-context7 should default to False."""
        from edison.cli.task.ready import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["task-001"])
        assert hasattr(args, "skip_context7")
        assert args.skip_context7 is False


class TestBypassBehavior:
    """Tests for --skip-context7 bypass behavior."""

    def test_bypass_allows_completion_without_context7_evidence(
        self, repo_with_context7_trigger: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With --skip-context7, task should complete even without Context7 markers."""
        from edison.cli.task.ready import main as ready_main

        task_id = "task-bypass-001"
        session_id = "test-session"

        _create_test_session(repo_with_context7_trigger, session_id)
        _create_wip_task_with_context7_trigger(
            repo_with_context7_trigger, task_id, session_id
        )

        args = argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=False,
            skip_context7=True,
            repo_root=repo_with_context7_trigger,
        )

        rc = ready_main(args)

        # Should succeed with bypass
        assert rc == 0

        # Verify the output confirms task was moved to done
        captured = capsys.readouterr()
        assert "done" in captured.out.lower(), f"Expected 'done' in output, got: {captured.out}"

    def test_bypass_prints_loud_warning(
        self, repo_with_context7_trigger: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """With --skip-context7, a loud warning must be printed."""
        from edison.cli.task.ready import main as ready_main

        task_id = "task-bypass-002"
        session_id = "test-session"

        _create_test_session(repo_with_context7_trigger, session_id)
        _create_wip_task_with_context7_trigger(
            repo_with_context7_trigger, task_id, session_id
        )

        args = argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=False,
            skip_context7=True,
            repo_root=repo_with_context7_trigger,
        )

        ready_main(args)

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Must have a warning about bypass
        assert "WARNING" in output.upper() or "BYPASS" in output.upper()
        assert "context7" in output.lower()

    def test_bypass_records_audit_trace(
        self, repo_with_context7_trigger: Path
    ) -> None:
        """With --skip-context7, an audit trace must be recorded."""
        from edison.cli.task.ready import main as ready_main

        task_id = "task-bypass-003"
        session_id = "test-session"

        _create_test_session(repo_with_context7_trigger, session_id)
        _create_wip_task_with_context7_trigger(
            repo_with_context7_trigger, task_id, session_id
        )

        args = argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=False,
            skip_context7=True,
            repo_root=repo_with_context7_trigger,
        )

        ready_main(args)

        # Check for audit trace in implementation report
        round_dir = (
            repo_with_context7_trigger
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
        )
        impl_report = round_dir / "implementation-report.md"
        assert impl_report.exists()

        content = impl_report.read_text(encoding="utf-8")

        # Must record the bypass
        assert "context7" in content.lower()
        assert "bypass" in content.lower() or "skip" in content.lower()


class TestBypassOnlyAffectsContext7:
    """Tests ensuring bypass only affects Context7, not other guards."""

    def test_bypass_does_not_skip_implementation_report_check(
        self, repo_with_context7_trigger: Path
    ) -> None:
        """--skip-context7 should not bypass implementation report requirement."""
        from edison.cli.task.ready import main as ready_main

        task_id = "task-no-impl"
        session_id = "test-session"

        _create_test_session(repo_with_context7_trigger, session_id)

        # Create task WITHOUT implementation report
        task_content = f"""---
id: "{task_id}"
title: "API Implementation"
session_id: "{session_id}"
---

# API Implementation
"""
        task_path = (
            repo_with_context7_trigger / ".project" / "tasks" / "wip" / f"{task_id}.md"
        )
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text(task_content, encoding="utf-8")

        # Create QA
        qa_content = f"""---
id: "{task_id}-qa"
task_id: "{task_id}"
title: "QA {task_id}"
session_id: "{session_id}"
---

# QA {task_id}
"""
        qa_path = (
            repo_with_context7_trigger / ".project" / "qa" / "waiting" / f"{task_id}-qa.md"
        )
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        qa_path.write_text(qa_content, encoding="utf-8")

        # No implementation report - should fail even with bypass
        args = argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=False,
            skip_context7=True,
            repo_root=repo_with_context7_trigger,
        )

        rc = ready_main(args)

        # Should fail - implementation report is still required
        assert rc != 0


class TestBypassJsonOutput:
    """Tests for --skip-context7 behavior with JSON output."""

    def test_bypass_json_output_includes_bypass_flag(
        self, repo_with_context7_trigger: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output should indicate Context7 was bypassed."""
        from edison.cli.task.ready import main as ready_main

        task_id = "task-bypass-json"
        session_id = "test-session"

        _create_test_session(repo_with_context7_trigger, session_id)
        _create_wip_task_with_context7_trigger(
            repo_with_context7_trigger, task_id, session_id
        )

        args = argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=True,
            skip_context7=True,
            repo_root=repo_with_context7_trigger,
        )

        rc = ready_main(args)
        assert rc == 0

        captured = capsys.readouterr()
        data = json.loads(captured.out)

        # JSON output should include bypass info
        assert "context7_bypassed" in data or "context7Bypassed" in data
