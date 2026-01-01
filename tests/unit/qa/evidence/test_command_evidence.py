"""Tests for command evidence v1 format parsing and validation.

Tests cover:
- Parsing YAML frontmatter from command evidence files
- Validating required keys in frontmatter
- Detecting non-zero exit codes
- Handling malformed/missing frontmatter
- Writing command evidence with proper format
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


class TestParseCommandEvidence:
    """Tests for parsing command evidence v1 format."""

    def test_parse_valid_evidence_with_exit_code_zero(self, tmp_path: Path) -> None:
        """Parse valid evidence file with exit code 0."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
All tests passed!
"""
        )

        result = parse_command_evidence(evidence_file)

        assert result is not None
        assert result["evidenceVersion"] == 1
        assert result["evidenceKind"] == "command"
        assert result["taskId"] == "task-001"
        assert result["round"] == 1
        assert result["commandName"] == "test"
        assert result["command"] == "pytest tests/"
        assert result["exitCode"] == 0
        assert result["pipefail"] is True
        assert result["output"] == "All tests passed!\n"

    def test_parse_evidence_with_non_zero_exit_code(self, tmp_path: Path) -> None:
        """Parse evidence file with non-zero exit code."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-002"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 1
---
FAILED: test_something.py
"""
        )

        result = parse_command_evidence(evidence_file)

        assert result is not None
        assert result["exitCode"] == 1
        assert "FAILED" in result["output"]

    def test_parse_evidence_without_frontmatter_returns_none(
        self, tmp_path: Path
    ) -> None:
        """Evidence without YAML frontmatter returns None."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text("Just plain output without frontmatter\n")

        result = parse_command_evidence(evidence_file)

        assert result is None

    def test_parse_evidence_with_malformed_yaml_returns_none(
        self, tmp_path: Path
    ) -> None:
        """Evidence with malformed YAML frontmatter returns None."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
taskId: [invalid yaml here
---
output
"""
        )

        result = parse_command_evidence(evidence_file)

        assert result is None

    def test_parse_evidence_with_missing_required_key_returns_none(
        self, tmp_path: Path
    ) -> None:
        """Evidence missing required keys returns None."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        # Missing exitCode key
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
---
output
"""
        )

        result = parse_command_evidence(evidence_file)

        assert result is None

    def test_parse_nonexistent_file_returns_none(self, tmp_path: Path) -> None:
        """Non-existent file returns None."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "does-not-exist.txt"

        result = parse_command_evidence(evidence_file)

        assert result is None

    def test_parse_evidence_with_empty_output(self, tmp_path: Path) -> None:
        """Parse evidence with empty output section."""
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "build"
command: "make build"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
"""
        )

        result = parse_command_evidence(evidence_file)

        assert result is not None
        assert result["exitCode"] == 0
        assert result["output"] == ""


class TestValidateCommandEvidence:
    """Tests for validating command evidence exit codes."""

    def test_validate_exit_code_zero_passes(self, tmp_path: Path) -> None:
        """Validation passes for exit code 0."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            validate_command_evidence,
        )

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
All tests passed!
"""
        )

        parsed = parse_command_evidence(evidence_file)
        assert parsed is not None

        is_valid, error = validate_command_evidence(parsed)

        assert is_valid is True
        assert error is None

    def test_validate_non_zero_exit_code_fails(self, tmp_path: Path) -> None:
        """Validation fails for non-zero exit code."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            validate_command_evidence,
        )

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 1
---
FAILED tests
"""
        )

        parsed = parse_command_evidence(evidence_file)
        assert parsed is not None

        is_valid, error = validate_command_evidence(parsed)

        assert is_valid is False
        assert error is not None
        assert "exitCode" in error.lower() or "exit" in error.lower()

    def test_validate_missing_pipefail_warns(self, tmp_path: Path) -> None:
        """Validation warns when pipefail is missing or false."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            validate_command_evidence,
        )

        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "pytest tests/"
cwd: "/home/user/project"
shell: "bash"
pipefail: false
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
output
"""
        )

        parsed = parse_command_evidence(evidence_file)
        assert parsed is not None

        # Should still pass but may have warning in tuple
        is_valid, error = validate_command_evidence(parsed)

        # Exit code 0 means valid, but pipefail=false is a potential issue
        assert is_valid is True


class TestWriteCommandEvidence:
    """Tests for writing command evidence v1 format."""

    def test_write_command_evidence_creates_file(self, tmp_path: Path) -> None:
        """Write command evidence creates properly formatted file."""
        from edison.core.qa.evidence.command_evidence import write_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        start_time = datetime(2025, 12, 31, 16, 33, 50, tzinfo=timezone.utc)
        end_time = datetime(2025, 12, 31, 16, 34, 12, tzinfo=timezone.utc)

        write_command_evidence(
            path=evidence_file,
            task_id="task-001",
            round_num=1,
            command_name="test",
            command="pytest tests/",
            cwd="/home/user/project",
            exit_code=0,
            output="All tests passed!\n",
            started_at=start_time,
            completed_at=end_time,
            shell="bash",
            pipefail=True,
        )

        assert evidence_file.exists()
        content = evidence_file.read_text()

        # Verify frontmatter structure
        assert content.startswith("---\n")
        assert "evidenceVersion: 1" in content
        assert 'evidenceKind: "command"' in content or "evidenceKind: command" in content
        assert 'taskId: "task-001"' in content or "taskId: task-001" in content
        assert "round: 1" in content
        assert "exitCode: 0" in content
        assert "pipefail: true" in content
        assert "All tests passed!" in content

    def test_write_command_evidence_with_multiline_output(
        self, tmp_path: Path
    ) -> None:
        """Write command evidence preserves multiline output."""
        from edison.core.qa.evidence.command_evidence import write_command_evidence

        evidence_file = tmp_path / "command-test.txt"
        multiline_output = """test_one.py::test_a PASSED
test_one.py::test_b PASSED
test_two.py::test_c FAILED

=== FAILURES ===
test_c: AssertionError
"""

        write_command_evidence(
            path=evidence_file,
            task_id="task-001",
            round_num=1,
            command_name="test",
            command="pytest tests/",
            cwd="/home/user/project",
            exit_code=1,
            output=multiline_output,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )

        content = evidence_file.read_text()
        assert "test_one.py::test_a PASSED" in content
        assert "AssertionError" in content

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        """Written evidence can be read back correctly."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            write_command_evidence,
        )

        evidence_file = tmp_path / "command-test.txt"
        start_time = datetime(2025, 12, 31, 16, 33, 50, tzinfo=timezone.utc)
        end_time = datetime(2025, 12, 31, 16, 34, 12, tzinfo=timezone.utc)

        write_command_evidence(
            path=evidence_file,
            task_id="task-123",
            round_num=2,
            command_name="lint",
            command="ruff check src/",
            cwd="/home/user/project",
            exit_code=0,
            output="All checks passed!",
            started_at=start_time,
            completed_at=end_time,
            shell="bash",
            pipefail=True,
        )

        result = parse_command_evidence(evidence_file)

        assert result is not None
        assert result["taskId"] == "task-123"
        assert result["round"] == 2
        assert result["commandName"] == "lint"
        assert result["command"] == "ruff check src/"
        assert result["exitCode"] == 0
        assert result["pipefail"] is True


class TestValidateCommandEvidenceFiles:
    """Tests for validating multiple command evidence files in a round directory."""

    def test_validate_all_files_pass(self, tmp_path: Path) -> None:
        """All command evidence files with exit code 0 pass validation."""
        from edison.core.qa.evidence.command_evidence import (
            validate_command_evidence_files,
            write_command_evidence,
        )

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        now = datetime.now(timezone.utc)

        for cmd_name in ["type-check", "lint", "test", "build"]:
            write_command_evidence(
                path=round_dir / f"command-{cmd_name}.txt",
                task_id="task-001",
                round_num=1,
                command_name=cmd_name,
                command=f"{cmd_name}-command",
                cwd="/project",
                exit_code=0,
                output=f"{cmd_name} passed",
                started_at=now,
                completed_at=now,
            )

        errors = validate_command_evidence_files(
            round_dir, ["command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"]
        )

        assert errors == []

    def test_validate_detects_missing_frontmatter(self, tmp_path: Path) -> None:
        """Detects files without proper frontmatter."""
        from edison.core.qa.evidence.command_evidence import validate_command_evidence_files

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        # Create file without frontmatter
        (round_dir / "command-test.txt").write_text("Just output, no frontmatter\n")

        errors = validate_command_evidence_files(round_dir, ["command-test.txt"])

        assert len(errors) == 1
        assert "command-test.txt" in errors[0]
        assert "frontmatter" in errors[0].lower() or "header" in errors[0].lower()

    def test_validate_detects_non_zero_exit_code(self, tmp_path: Path) -> None:
        """Detects files with non-zero exit codes."""
        from edison.core.qa.evidence.command_evidence import (
            validate_command_evidence_files,
            write_command_evidence,
        )

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        now = datetime.now(timezone.utc)

        # One passing, one failing
        write_command_evidence(
            path=round_dir / "command-lint.txt",
            task_id="task-001",
            round_num=1,
            command_name="lint",
            command="ruff check",
            cwd="/project",
            exit_code=0,
            output="lint passed",
            started_at=now,
            completed_at=now,
        )

        write_command_evidence(
            path=round_dir / "command-test.txt",
            task_id="task-001",
            round_num=1,
            command_name="test",
            command="pytest",
            cwd="/project",
            exit_code=1,
            output="test failed",
            started_at=now,
            completed_at=now,
        )

        errors = validate_command_evidence_files(
            round_dir, ["command-lint.txt", "command-test.txt"]
        )

        assert len(errors) == 1
        assert "command-test.txt" in errors[0]
        assert "exit" in errors[0].lower()

    def test_validate_detects_missing_file(self, tmp_path: Path) -> None:
        """Detects missing required evidence files."""
        from edison.core.qa.evidence.command_evidence import validate_command_evidence_files

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        errors = validate_command_evidence_files(
            round_dir, ["command-test.txt", "command-lint.txt"]
        )

        assert len(errors) == 2
        assert any("command-test.txt" in e for e in errors)
        assert any("command-lint.txt" in e for e in errors)


class TestPipefailBehavior:
    """Tests verifying pipefail captures pipeline failures correctly."""

    def test_evidence_with_pipefail_true_and_exit_one(self, tmp_path: Path) -> None:
        """When pipefail=true and exitCode=1, command failed correctly."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            validate_command_evidence,
        )

        # This simulates: `false | tee output.txt` with pipefail=true
        # The exit code should be 1 from `false`
        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "false | tee /dev/null"
cwd: "/home/user/project"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 1
---
"""
        )

        parsed = parse_command_evidence(evidence_file)
        assert parsed is not None
        assert parsed["exitCode"] == 1
        assert parsed["pipefail"] is True

        is_valid, error = validate_command_evidence(parsed)
        assert is_valid is False
        assert error is not None

    def test_evidence_without_pipefail_may_mask_failures(self, tmp_path: Path) -> None:
        """Without pipefail, exit code 0 may be masking pipeline failures."""
        from edison.core.qa.evidence.command_evidence import (
            parse_command_evidence,
            validate_command_evidence,
        )

        # This simulates: `false | tee output.txt` WITHOUT pipefail
        # The exit code would be 0 from `tee` (masking the `false` failure)
        evidence_file = tmp_path / "command-test.txt"
        evidence_file.write_text(
            """---
evidenceVersion: 1
evidenceKind: "command"
taskId: "task-001"
round: 1
commandName: "test"
command: "false | tee /dev/null"
cwd: "/home/user/project"
shell: "bash"
pipefail: false
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
"""
        )

        parsed = parse_command_evidence(evidence_file)
        assert parsed is not None
        assert parsed["exitCode"] == 0
        assert parsed["pipefail"] is False

        # This is technically valid (exit code 0), but pipefail=false
        # The validation should still pass but the data shows the risk
        is_valid, error = validate_command_evidence(parsed)
        assert is_valid is True
