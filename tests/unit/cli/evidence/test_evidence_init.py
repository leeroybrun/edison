"""Tests for edison evidence init command.

TDD: RED phase - These tests are written BEFORE implementation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Generator

import pytest
import yaml

from edison.core.config.cache import clear_all_caches


@pytest.fixture
def edison_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a minimal Edison project structure."""
    # Clear config caches to ensure tests use isolated config
    clear_all_caches()

    # Create .git to make it a valid repo root
    (tmp_path / ".git").mkdir()

    # Create .project structure
    project_dir = tmp_path / ".project"
    project_dir.mkdir()
    (project_dir / "tasks").mkdir()
    (project_dir / "tasks" / "wip").mkdir()

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

    # Create ci.yaml with commands config
    ci_config = {
        "ci": {
            "commands": {
                "type-check": "mypy src",
                "lint": "ruff check src",
                "test": "pytest tests -v",
                "build": "python -m build",
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


class TestEvidenceInit:
    """Tests for evidence init command."""

    def test_evidence_init_creates_round_directory(self, edison_project: Path) -> None:
        """evidence init should create the evidence round directory."""
        from edison.cli.evidence.init import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project)])

        result = main(args)

        assert result == 0
        evidence_dir = edison_project / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        assert evidence_dir.exists()

    def test_evidence_init_creates_implementation_report_stub(self, edison_project: Path) -> None:
        """evidence init should create an implementation-report.md stub."""
        from edison.cli.evidence.init import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project)])

        result = main(args)

        assert result == 0
        report_path = edison_project / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1" / "implementation-report.md"
        assert report_path.exists()

        content = report_path.read_text()
        # Should have YAML frontmatter
        assert content.startswith("---")
        assert "taskId:" in content

    def test_evidence_init_report_has_required_fields(self, edison_project: Path) -> None:
        """Implementation report stub should have all required schema fields."""
        from edison.cli.evidence.init import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project)])

        main(args)

        report_path = edison_project / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1" / "implementation-report.md"
        content = report_path.read_text()

        # Parse frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3
        frontmatter = yaml.safe_load(parts[1])

        # Check required fields from schema
        required = ["taskId", "round", "implementationApproach", "primaryModel",
                   "completionStatus", "followUpTasks", "notesForValidator", "tracking"]
        for field in required:
            assert field in frontmatter, f"Missing required field: {field}"

    def test_evidence_init_explicit_round_number(self, edison_project: Path) -> None:
        """evidence init with --round should create that specific round."""
        from edison.cli.evidence.init import main, register_args

        # First create round 1
        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project)])
        main(args)

        # Then create round 2
        args = parser.parse_args(["test-task-123", "--round", "2", "--repo-root", str(edison_project)])
        result = main(args)

        assert result == 0
        round2_dir = edison_project / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-2"
        assert round2_dir.exists()

    def test_evidence_init_idempotent(self, edison_project: Path) -> None:
        """Running init twice should not overwrite existing report."""
        from edison.cli.evidence.init import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--repo-root", str(edison_project)])

        # First init
        main(args)

        report_path = edison_project / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1" / "implementation-report.md"
        original_content = report_path.read_text()

        # Second init - should not overwrite
        result = main(args)

        assert result == 0
        assert report_path.read_text() == original_content

    def test_evidence_init_json_output(self, edison_project: Path) -> None:
        """evidence init --json should output JSON."""
        import json
        from io import StringIO
        from unittest.mock import patch

        from edison.cli.evidence.init import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["test-task-123", "--json", "--repo-root", str(edison_project)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        data = json.loads(output)
        assert "round" in data
        assert "evidencePath" in data
