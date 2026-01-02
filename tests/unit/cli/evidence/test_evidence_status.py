"""Tests for edison evidence status command.

TDD: RED phase - These tests are written BEFORE implementation.
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
def edison_project_with_evidence(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a project with partial evidence files."""
    # Clear config caches to ensure tests use isolated config
    clear_all_caches()

    # Create .git to make it a valid repo root
    (tmp_path / ".git").mkdir()

    # Create .project structure
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    (project_dir / "tasks").mkdir()
    (project_dir / "tasks" / "wip").mkdir()

    # Create evidence directory with round-1
    evidence_dir = project_dir / "qa" / "validation-evidence" / "test-task-123" / "round-1"
    evidence_dir.mkdir(parents=True)

    # Create some evidence files (but not all)
    (evidence_dir / "command-type-check.txt").write_text(
        """---
evidenceVersion: 1
evidenceKind: command
taskId: test-task-123
round: 1
commandName: type-check
command: mypy src
cwd: /path/to/project
exitCode: 0
---
Success
"""
    )
    (evidence_dir / "command-lint.txt").write_text(
        """---
evidenceVersion: 1
evidenceKind: command
taskId: test-task-123
round: 1
commandName: lint
command: ruff check src
cwd: /path/to/project
exitCode: 1
---
Error: lint failure
"""
    )
    # command-test.txt and command-build.txt are MISSING

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
                    "command-build.txt",
                ],
                "files": {
                    "type-check": "command-type-check.txt",
                    "lint": "command-lint.txt",
                    "test": "command-test.txt",
                    "build": "command-build.txt",
                },
            },
            "defaultSessionId": "test-session",
        },
    }
    (config_dir / "qa.yaml").write_text(yaml.safe_dump(qa_config))

    # Create a task file
    task_dir = project_dir / "tasks" / "wip"
    task_file = task_dir / "test-task-123.md"
    task_content = """---
id: test-task-123
title: Test Task
status: wip
---

# Test Task
"""
    task_file.write_text(task_content)

    yield tmp_path

    # Clear caches after test
    clear_all_caches()


class TestEvidenceStatus:
    """Tests for evidence status command."""

    def test_evidence_status_shows_present_files(self, edison_project_with_evidence: Path) -> None:
        """evidence status should list present evidence files."""
        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        # Note: result is 1 because fixture has missing files and failed commands
        # This test verifies present files are listed regardless of exit code
        output = stdout.getvalue()
        assert "command-type-check.txt" in output
        assert "command-lint.txt" in output

    def test_evidence_status_shows_missing_files(self, edison_project_with_evidence: Path) -> None:
        """evidence status should identify missing required files."""
        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        # Should exit non-zero when files are missing
        assert result == 1
        output = stdout.getvalue()
        assert "command-test.txt" in output
        assert "command-build.txt" in output
        assert "missing" in output.lower()

    def test_evidence_status_shows_failed_commands(self, edison_project_with_evidence: Path) -> None:
        """evidence status should identify commands that failed (exitCode != 0)."""
        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            main(args)

        output = stdout.getvalue()
        # lint had exitCode: 1
        assert "lint" in output.lower()
        assert "fail" in output.lower() or "error" in output.lower()

    def test_evidence_status_json_output(self, edison_project_with_evidence: Path) -> None:
        """evidence status --json should output structured JSON."""
        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--json", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            main(args)

        output = stdout.getvalue()
        data = json.loads(output)
        assert "present" in data
        assert "missing" in data
        assert "failed" in data
        assert "command-type-check.txt" in data["present"]
        assert "command-test.txt" in data["missing"]

    def test_evidence_status_explicit_round(self, edison_project_with_evidence: Path) -> None:
        """evidence status --round should check specific round."""
        # Create empty round-2 directory
        evidence_dir = edison_project_with_evidence / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-2"
        evidence_dir.mkdir(parents=True)

        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--round", "2", "--json", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            main(args)

        output = stdout.getvalue()
        data = json.loads(output)
        # Round 2 should have all files missing
        assert len(data["missing"]) == 4
        assert len(data["present"]) == 0

    def test_evidence_status_exit_code_success(self, edison_project_with_evidence: Path) -> None:
        """evidence status should exit 0 when all required files present and pass."""
        # Add the missing files with success exit codes
        evidence_dir = edison_project_with_evidence / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"

        (evidence_dir / "command-test.txt").write_text(
            """---
evidenceVersion: 1
evidenceKind: command
taskId: test-task-123
round: 1
commandName: test
command: pytest tests
cwd: /path/to/project
exitCode: 0
---
Tests passed
"""
        )
        (evidence_dir / "command-build.txt").write_text(
            """---
evidenceVersion: 1
evidenceKind: command
taskId: test-task-123
round: 1
commandName: build
command: python -m build
cwd: /path/to/project
exitCode: 0
---
Build succeeded
"""
        )
        # Fix the lint file to have exitCode 0
        (evidence_dir / "command-lint.txt").write_text(
            """---
evidenceVersion: 1
evidenceKind: command
taskId: test-task-123
round: 1
commandName: lint
command: ruff check src
cwd: /path/to/project
exitCode: 0
---
No issues found
"""
        )

        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_evidence)])

        result = main(args)

        assert result == 0

    def test_evidence_status_shows_round_number(self, edison_project_with_evidence: Path) -> None:
        """evidence status should display which round is being checked."""
        from edison.cli.evidence.status import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--json", "--repo-root", str(edison_project_with_evidence)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            main(args)

        output = stdout.getvalue()
        data = json.loads(output)
        assert "round" in data
        assert data["round"] == 1
