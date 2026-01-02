"""Tests for edison evidence capture command.

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
def edison_project_with_round(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a minimal Edison project with an existing evidence round."""
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

    # Create ci.yaml with commands config - use simple commands that work on any system
    # NOTE: Must explicitly set unused commands to null to override defaults from base config
    ci_config = {
        "ci": {
            "commands": {
                "type-check": "echo 'type-check passed'",
                "lint": "echo 'lint passed'",
                "test": "echo 'test passed'",
                "build": "echo 'build passed'",
                # Override base config placeholders with null
                "format": None,
                "format-check": None,
                "test-coverage": None,
                "dev": None,
                "dependency-audit": None,
            },
        },
    }
    (config_dir / "ci.yaml").write_text(yaml.safe_dump(ci_config))

    # Create a task file
    task_dir = project_dir / "tasks" / "wip"
    task_file = task_dir / "test-task-123.md"
    task_content = """---
id: test-task-123
title: Test Task
status: wip
---

# Test Task

Implementation details here.
"""
    task_file.write_text(task_content)

    yield tmp_path

    # Clear caches after test
    clear_all_caches()


class TestEvidenceCapture:
    """Tests for evidence capture command."""

    def test_evidence_capture_runs_configured_commands(self, edison_project_with_round: Path) -> None:
        """evidence capture should run all configured CI commands."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_round)])

        result = main(args)

        assert result == 0

        # Check that all command output files were created
        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        assert (evidence_dir / "command-type-check.txt").exists()
        assert (evidence_dir / "command-lint.txt").exists()
        assert (evidence_dir / "command-test.txt").exists()
        assert (evidence_dir / "command-build.txt").exists()

    def test_evidence_capture_writes_yaml_frontmatter(self, edison_project_with_round: Path) -> None:
        """Command evidence files should have YAML frontmatter with metadata."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_round)])

        main(args)

        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        content = (evidence_dir / "command-type-check.txt").read_text()

        # Should have YAML frontmatter
        assert content.startswith("---")
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Check required frontmatter keys
        assert frontmatter["evidenceVersion"] == 1
        assert frontmatter["evidenceKind"] == "command"
        assert frontmatter["taskId"] == "test-task-123"
        assert frontmatter["round"] == 1
        assert frontmatter["commandName"] == "type-check"
        assert "command" in frontmatter
        assert "exitCode" in frontmatter
        assert "startedAt" in frontmatter
        assert "completedAt" in frontmatter

    def test_evidence_capture_records_exit_codes(self, edison_project_with_round: Path) -> None:
        """Capture should record actual exit codes from commands."""
        # Update ci.yaml with a failing command
        config_dir = edison_project_with_round / ".edison" / "config"
        ci_config = {
            "ci": {
                "commands": {
                    "type-check": "exit 1",  # Simulate failure
                    "lint": "echo 'lint passed'",
                    "test": "echo 'test passed'",
                    "build": "echo 'build passed'",
                },
            },
        }
        (config_dir / "ci.yaml").write_text(yaml.safe_dump(ci_config))

        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        # Use --continue to not stop on first failure
        args = parser.parse_args(["test-task-123", "--continue", "--repo-root", str(edison_project_with_round)])

        # Command may still exit 0 even if some tests fail (when using --continue)
        main(args)

        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        content = (evidence_dir / "command-type-check.txt").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Exit code should be non-zero for the failing command
        assert frontmatter["exitCode"] != 0

    def test_evidence_capture_specific_command(self, edison_project_with_round: Path) -> None:
        """evidence capture --command should run only specified command."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--command", "lint", "--repo-root", str(edison_project_with_round)])

        result = main(args)

        assert result == 0

        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        # Only lint should be created
        assert (evidence_dir / "command-lint.txt").exists()
        # Others should NOT be created
        assert not (evidence_dir / "command-type-check.txt").exists()
        assert not (evidence_dir / "command-test.txt").exists()
        assert not (evidence_dir / "command-build.txt").exists()

    def test_evidence_capture_explicit_round(self, edison_project_with_round: Path) -> None:
        """evidence capture --round should write to specified round."""
        # Create round-2 directory
        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-2"
        evidence_dir.mkdir(parents=True)

        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--round", "2", "--repo-root", str(edison_project_with_round)])

        result = main(args)

        assert result == 0
        assert (evidence_dir / "command-type-check.txt").exists()

    def test_evidence_capture_uses_pipefail(self, edison_project_with_round: Path) -> None:
        """Capture should use pipefail to catch pipeline failures."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_round)])

        main(args)

        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        content = (evidence_dir / "command-type-check.txt").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Should have pipefail enabled
        assert frontmatter.get("pipefail") is True

    def test_evidence_capture_json_output(self, edison_project_with_round: Path) -> None:
        """evidence capture --json should output JSON summary."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--json", "--repo-root", str(edison_project_with_round)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        data = json.loads(output)
        assert "commands" in data
        assert "passed" in data
        assert "failed" in data

    def test_evidence_capture_cwd_is_project_root(self, edison_project_with_round: Path) -> None:
        """Commands should run with cwd set to project root."""
        from edison.cli.evidence.capture import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project_with_round)])

        main(args)

        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        content = (evidence_dir / "command-type-check.txt").read_text()
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        # cwd should be the project root
        assert frontmatter["cwd"] == str(edison_project_with_round)
