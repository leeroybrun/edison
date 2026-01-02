"""Tests for edison task ready --run deprecation.

TDD: RED phase - These tests are written BEFORE implementation.

The --run flag was a legacy stub that generated placeholder evidence with failing
exit codes. Evidence must come from real runners, so --run should error with a
helpful message pointing users to the proper evidence commands.
"""
from __future__ import annotations

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
import yaml

from edison.core.config.cache import clear_all_caches


@pytest.fixture
def edison_project_with_task(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a minimal Edison project with a task in wip state."""
    # Clear config caches to ensure tests use isolated config
    clear_all_caches()

    # Create .git to make it a valid repo root
    (tmp_path / ".git").mkdir()

    # Create .project structure
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    tasks_dir = project_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "wip").mkdir()
    (tasks_dir / "done").mkdir()
    (tasks_dir / "todo").mkdir()

    # Create evidence directory structure
    evidence_dir = project_dir / "qa" / "validation-evidence" / "test-task-001"
    evidence_dir.mkdir(parents=True)

    # Create .edison config directory
    edison_dir = tmp_path / ".edison"
    edison_dir.mkdir()
    config_dir = edison_dir / "config"
    config_dir.mkdir()

    # Create qa.yaml with evidence config
    qa_config = {
        "validation": {
            "evidence": {
                "requiredFiles": [
                    "command-type-check.txt",
                    "command-lint.txt",
                    "command-test.txt",
                ],
                "files": {
                    "type-check": "command-type-check.txt",
                    "lint": "command-lint.txt",
                    "test": "command-test.txt",
                },
            },
            "defaultSessionId": "test-session",
        },
    }
    (config_dir / "qa.yaml").write_text(yaml.safe_dump(qa_config))

    # Create workflow.yaml config
    workflow_config = {
        "workflow": {
            "entities": {
                "task": {
                    "states": {
                        "todo": {"directory": "todo", "semantic": "todo"},
                        "wip": {"directory": "wip", "semantic": "wip"},
                        "done": {"directory": "done", "semantic": "done"},
                        "blocked": {"directory": "blocked", "semantic": "blocked"},
                    },
                    "defaultState": "todo",
                },
            },
        },
    }
    (config_dir / "workflow.yaml").write_text(yaml.safe_dump(workflow_config))

    # Create session.yaml with test session
    session_yaml = {
        "session": {
            "defaultSessionId": "test-session",
        },
    }
    (config_dir / "session.yaml").write_text(yaml.safe_dump(session_yaml))

    # Create sessions directory with current session (nested layout)
    sessions_dir = project_dir / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "wip").mkdir()
    session_dir = sessions_dir / "wip" / "test-session"
    session_dir.mkdir()
    (session_dir / "session.json").write_text(
        json.dumps({
            "id": "test-session",
            "state": "wip",
        })
    )

    # Create a task file in wip state
    task_dir = tasks_dir / "wip"
    task_file = task_dir / "test-task-001.md"
    task_content = """---
id: test-task-001
title: Test Task for Ready Deprecation
status: wip
session: test-session
---

# Test Task

Implementation details here.
"""
    task_file.write_text(task_content)

    yield tmp_path

    # Clear caches after test
    clear_all_caches()


class TestTaskReadyRunDeprecation:
    """Tests for --run flag deprecation on task ready command."""

    def test_run_flag_is_recognized(self, edison_project_with_task: Path) -> None:
        """The --run flag should be recognized by argparse (not unknown)."""
        from edison.cli.task.ready import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        # Should not raise SystemExit for unrecognized argument
        args = parser.parse_args(["test-task-001", "--run"])
        assert hasattr(args, "run") or hasattr(args, "run_deprecated")

    def test_run_flag_produces_error_exit_code(self, edison_project_with_task: Path) -> None:
        """Using --run should produce a non-zero exit code."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--repo-root",
            str(edison_project_with_task),
        ])

        result = main(args)

        # Should fail because --run is deprecated
        assert result != 0

    def test_run_flag_error_message_mentions_evidence_init(
        self, edison_project_with_task: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Error message should mention 'edison evidence init'."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--repo-root",
            str(edison_project_with_task),
        ])

        main(args)

        captured = capsys.readouterr()
        # Check stderr (where errors go)
        output = captured.err.lower()
        assert "evidence init" in output or "evidence init" in captured.out.lower()

    def test_run_flag_error_message_mentions_evidence_capture(
        self, edison_project_with_task: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Error message should mention 'edison evidence capture'."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--repo-root",
            str(edison_project_with_task),
        ])

        main(args)

        captured = capsys.readouterr()
        output = captured.err.lower()
        assert "evidence capture" in output or "evidence capture" in captured.out.lower()

    def test_run_flag_error_message_mentions_evidence_status(
        self, edison_project_with_task: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Error message should mention 'edison evidence status'."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--repo-root",
            str(edison_project_with_task),
        ])

        main(args)

        captured = capsys.readouterr()
        output = captured.err.lower()
        assert "evidence status" in output or "evidence status" in captured.out.lower()

    def test_run_flag_does_not_write_command_evidence(
        self, edison_project_with_task: Path
    ) -> None:
        """Using --run should NOT create any command-*.txt evidence files."""
        from edison.cli.task.ready import main, register_args

        evidence_dir = (
            edison_project_with_task / ".project" / "qa" / "validation-evidence" / "test-task-001"
        )

        # Count evidence files before
        evidence_files_before = list(evidence_dir.glob("**/command-*.txt"))

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--repo-root",
            str(edison_project_with_task),
        ])

        main(args)

        # Count evidence files after
        evidence_files_after = list(evidence_dir.glob("**/command-*.txt"))

        # No new command evidence files should be created
        assert len(evidence_files_after) == len(evidence_files_before)

    def test_run_flag_json_mode_returns_error(
        self, edison_project_with_task: Path
    ) -> None:
        """Using --run with --json should return error in JSON format."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--json",
            "--repo-root",
            str(edison_project_with_task),
        ])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result != 0
        output = stdout.getvalue()
        data = json.loads(output)
        assert "error" in data or "message" in data

    def test_run_flag_with_session(
        self, edison_project_with_task: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Using --run with --session should still produce deprecation error."""
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--run",
            "--session",
            "test-session",
            "--repo-root",
            str(edison_project_with_task),
        ])

        result = main(args)

        # Should still fail with deprecation error
        assert result != 0

        captured = capsys.readouterr()
        # Check that it mentions the correct alternative commands
        output = captured.err.lower() + captured.out.lower()
        assert "evidence" in output

    def test_ready_without_run_flag_does_not_trigger_deprecation(
        self, edison_project_with_task: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Normal ready command without --run should not trigger --run deprecation error.

        Note: The command may fail for other reasons (missing evidence, etc.) but
        it should NOT fail with the --run deprecation message.
        """
        from edison.cli.task.ready import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "test-task-001",
            "--session",
            "test-session",
            "--repo-root",
            str(edison_project_with_task),
        ])

        result = main(args)

        captured = capsys.readouterr()
        output = captured.err.lower() + captured.out.lower()

        # Should NOT contain the deprecation message specific to --run flag
        assert "the '--run' flag has been removed" not in output
        # If it fails, it should be for other reasons (like missing evidence)
        # not for --run deprecation
        assert "run_flag_deprecated" not in output
