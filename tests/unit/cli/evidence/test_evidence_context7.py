"""Tests for edison evidence context7 command.

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
    """Create a minimal Edison project with an evidence round."""
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

    # Create qa.yaml
    qa_config = {
        "validation": {
            "evidence": {
                "requiredFiles": [
                    "command-type-check.txt",
                    "command-lint.txt",
                    "command-test.txt",
                    "command-build.txt",
                ],
            },
            "defaultSessionId": "test-session",
        },
    }
    (config_dir / "qa.yaml").write_text(yaml.safe_dump(qa_config))

    # Create context7.yaml with post-training packages
    context7_config = {
        "context7": {
            "postTrainingPackages": ["fastapi", "pydantic", "pytest"],
        },
    }
    (config_dir / "context7.yaml").write_text(yaml.safe_dump(context7_config))

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


class TestEvidenceContext7Template:
    """Tests for evidence context7 template subcommand."""

    def test_context7_template_outputs_yaml(self, edison_project_with_round: Path) -> None:
        """context7 template should output YAML template for marker file."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["template", "fastapi", "--repo-root", str(edison_project_with_round)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        # Should be valid YAML
        data = yaml.safe_load(output)
        assert "package" in data
        assert data["package"] == "fastapi"
        assert "libraryId" in data
        assert "topics" in data

    def test_context7_template_includes_required_fields(self, edison_project_with_round: Path) -> None:
        """Template should include all required context7 marker fields."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["template", "pydantic", "--repo-root", str(edison_project_with_round)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            main(args)

        output = stdout.getvalue()
        data = yaml.safe_load(output)

        required_fields = ["package", "libraryId", "topics", "queriedAt"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestEvidenceContext7Save:
    """Tests for evidence context7 save subcommand."""

    def test_context7_save_creates_marker_file(self, edison_project_with_round: Path) -> None:
        """context7 save should create the marker file in evidence directory."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "save", "test-task-123", "fastapi",
            "--library-id", "/tiangolo/fastapi",
            "--topics", "routing,dependencies",
            "--repo-root", str(edison_project_with_round),
        ])

        result = main(args)

        assert result == 0
        marker_path = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1" / "context7-fastapi.txt"
        assert marker_path.exists()

    def test_context7_save_validates_required_fields(self, edison_project_with_round: Path) -> None:
        """context7 save should fail if required fields are missing."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        # Missing --library-id
        args = parser.parse_args([
            "save", "test-task-123", "fastapi",
            "--topics", "routing",
            "--repo-root", str(edison_project_with_round),
        ])

        result = main(args)

        # Should fail without library-id
        assert result != 0

    def test_context7_save_marker_format(self, edison_project_with_round: Path) -> None:
        """Saved marker file should have proper YAML frontmatter format."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "save", "test-task-123", "pytest",
            "--library-id", "/pytest-dev/pytest",
            "--topics", "fixtures,parametrize",
            "--repo-root", str(edison_project_with_round),
        ])

        main(args)

        marker_path = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1" / "context7-pytest.txt"
        content = marker_path.read_text()

        # Should have frontmatter
        assert content.startswith("---")
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        assert frontmatter["package"] == "pytest"
        assert frontmatter["libraryId"] == "/pytest-dev/pytest"
        assert "fixtures" in frontmatter["topics"]
        assert "queriedAt" in frontmatter

    def test_context7_save_explicit_round(self, edison_project_with_round: Path) -> None:
        """context7 save --round should save to specific round."""
        # Create round-2 directory
        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-2"
        evidence_dir.mkdir(parents=True)

        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "save", "test-task-123", "fastapi",
            "--library-id", "/tiangolo/fastapi",
            "--topics", "routing",
            "--round", "2",
            "--repo-root", str(edison_project_with_round),
        ])

        result = main(args)

        assert result == 0
        marker_path = evidence_dir / "context7-fastapi.txt"
        assert marker_path.exists()

    def test_context7_save_json_output(self, edison_project_with_round: Path) -> None:
        """context7 save --json should output JSON confirmation."""
        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "save", "test-task-123", "fastapi",
            "--library-id", "/tiangolo/fastapi",
            "--topics", "routing",
            "--json",
            "--repo-root", str(edison_project_with_round),
        ])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        data = json.loads(output)
        assert "path" in data
        assert "package" in data


class TestEvidenceContext7List:
    """Tests for evidence context7 list subcommand."""

    def test_context7_list_shows_saved_markers(self, edison_project_with_round: Path) -> None:
        """context7 list should show all context7 markers in evidence directory."""
        # Create some marker files
        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        (evidence_dir / "context7-fastapi.txt").write_text(
            """---
package: fastapi
libraryId: /tiangolo/fastapi
topics: [routing]
queriedAt: "2025-01-01T00:00:00Z"
---
"""
        )
        (evidence_dir / "context7-pytest.txt").write_text(
            """---
package: pytest
libraryId: /pytest-dev/pytest
topics: [fixtures]
queriedAt: "2025-01-01T00:00:00Z"
---
"""
        )

        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["list", "test-task-123", "--repo-root", str(edison_project_with_round)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        assert "fastapi" in output
        assert "pytest" in output

    def test_context7_list_json_output(self, edison_project_with_round: Path) -> None:
        """context7 list --json should output structured JSON."""
        evidence_dir = edison_project_with_round / ".project" / "qa" / "validation-evidence" / "test-task-123" / "round-1"
        (evidence_dir / "context7-fastapi.txt").write_text(
            """---
package: fastapi
libraryId: /tiangolo/fastapi
topics: [routing, dependencies]
queriedAt: "2025-01-01T00:00:00Z"
---
"""
        )

        from edison.cli.evidence.context7 import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["list", "test-task-123", "--json", "--repo-root", str(edison_project_with_round)])

        stdout = StringIO()
        with patch.object(sys, "stdout", stdout):
            result = main(args)

        assert result == 0
        output = stdout.getvalue()
        data = json.loads(output)
        assert "markers" in data
        assert len(data["markers"]) == 1
        assert data["markers"][0]["package"] == "fastapi"
