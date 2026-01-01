"""Tests for TDD ready gate validation."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


class TestValidateCommandEvidenceExitCodes:
    """Tests for validate_command_evidence_exit_codes function."""

    def test_all_files_valid_returns_empty_errors(self, tmp_path: Path) -> None:
        """All valid evidence files returns no errors."""
        from edison.core.tdd.ready_gate import validate_command_evidence_exit_codes
        from edison.core.qa.evidence.command_evidence import write_command_evidence

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        now = datetime.now(timezone.utc)
        for cmd_name in ["test", "lint"]:
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

        errors = validate_command_evidence_exit_codes(
            round_dir, ["command-test.txt", "command-lint.txt"]
        )

        assert errors == []

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        """Missing evidence file returns error."""
        from edison.core.tdd.ready_gate import validate_command_evidence_exit_codes

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        errors = validate_command_evidence_exit_codes(
            round_dir, ["command-test.txt"]
        )

        assert len(errors) == 1
        assert errors[0].filename == "command-test.txt"
        assert "Missing" in errors[0].message
        assert errors[0].command_name == "test"

    def test_missing_frontmatter_returns_error(self, tmp_path: Path) -> None:
        """File without frontmatter returns error."""
        from edison.core.tdd.ready_gate import validate_command_evidence_exit_codes

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()
        (round_dir / "command-test.txt").write_text("Just output, no frontmatter\n")

        errors = validate_command_evidence_exit_codes(
            round_dir, ["command-test.txt"]
        )

        assert len(errors) == 1
        assert "frontmatter" in errors[0].message.lower()

    def test_non_zero_exit_code_returns_error(self, tmp_path: Path) -> None:
        """Non-zero exit code returns error."""
        from edison.core.tdd.ready_gate import validate_command_evidence_exit_codes
        from edison.core.qa.evidence.command_evidence import write_command_evidence

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        now = datetime.now(timezone.utc)
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

        errors = validate_command_evidence_exit_codes(
            round_dir, ["command-test.txt"]
        )

        assert len(errors) == 1
        assert "exit" in errors[0].message.lower()

    def test_ci_commands_included_in_error(self, tmp_path: Path) -> None:
        """CI commands are included in error for actionable fixes."""
        from edison.core.tdd.ready_gate import validate_command_evidence_exit_codes

        round_dir = tmp_path / "round-1"
        round_dir.mkdir()

        ci_commands = {
            "test": "pytest tests/",
            "lint": "ruff check src/",
        }

        errors = validate_command_evidence_exit_codes(
            round_dir,
            ["command-test.txt", "command-lint.txt"],
            ci_commands=ci_commands,
        )

        assert len(errors) == 2
        test_error = next(e for e in errors if e.command_name == "test")
        lint_error = next(e for e in errors if e.command_name == "lint")

        assert test_error.configured_command == "pytest tests/"
        assert lint_error.configured_command == "ruff check src/"


class TestScanForBlockedTestTokens:
    """Tests for scan_for_blocked_test_tokens function."""

    def test_no_tokens_returns_empty(self, tmp_path: Path) -> None:
        """Clean files return no errors."""
        from edison.core.tdd.ready_gate import scan_for_blocked_test_tokens

        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_something():
    assert True

def test_another():
    assert 1 == 1
""")

        errors = scan_for_blocked_test_tokens([test_file])

        assert errors == []

    def test_detects_only_token(self, tmp_path: Path) -> None:
        """Detects .only token."""
        from edison.core.tdd.ready_gate import scan_for_blocked_test_tokens

        test_file = tmp_path / "test_example.ts"
        test_file.write_text("""
describe('example', () => {
    it.only('should work', () => {
        expect(true).toBe(true);
    });
});
""")

        errors = scan_for_blocked_test_tokens([test_file])

        assert len(errors) == 1
        assert errors[0].token == "it.only("
        assert errors[0].line_number == 3

    def test_detects_skip_token(self, tmp_path: Path) -> None:
        """Detects .skip token."""
        from edison.core.tdd.ready_gate import scan_for_blocked_test_tokens

        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
import pytest

@pytest.mark.skip
def test_something():
    assert True
""")

        errors = scan_for_blocked_test_tokens([test_file])

        assert len(errors) == 1
        assert "@pytest.mark.skip" in errors[0].token

    def test_detects_multiple_tokens(self, tmp_path: Path) -> None:
        """Detects multiple blocked tokens."""
        from edison.core.tdd.ready_gate import scan_for_blocked_test_tokens

        test_file = tmp_path / "test_example.ts"
        test_file.write_text("""
describe.only('focused', () => {
    it.only('test1', () => {});
    xit('skipped', () => {});
});
""")

        errors = scan_for_blocked_test_tokens([test_file])

        assert len(errors) >= 3  # describe.only, it.only, xit

    def test_custom_tokens_supported(self, tmp_path: Path) -> None:
        """Custom tokens can be added."""
        from edison.core.tdd.ready_gate import scan_for_blocked_test_tokens

        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
# TODO: fix this test
def test_broken():
    pass
""")

        custom = {"TODO:": "Unfinished work"}
        errors = scan_for_blocked_test_tokens([test_file], custom_tokens=custom)

        assert len(errors) == 1
        assert errors[0].token == "TODO:"


class TestFormatEvidenceErrorMessage:
    """Tests for format_evidence_error_message function."""

    def test_formats_comprehensive_message(self, tmp_path: Path) -> None:
        """Formats comprehensive error message."""
        from edison.core.tdd.ready_gate import (
            CommandEvidenceError,
            format_evidence_error_message,
        )

        round_dir = tmp_path / "round-1"
        errors = [
            CommandEvidenceError(
                filename="command-test.txt",
                message="Missing evidence file",
                command_name="test",
                configured_command="pytest tests/",
            ),
            CommandEvidenceError(
                filename="command-lint.txt",
                message="exitCode was 1",
                command_name="lint",
                configured_command="ruff check src/",
            ),
        ]

        message = format_evidence_error_message(
            task_id="task-001",
            round_num=1,
            round_dir=round_dir,
            errors=errors,
            ci_commands={"test": "pytest tests/", "lint": "ruff check src/"},
        )

        assert "task-001" in message
        assert "round-1" in message
        assert "command-test.txt" in message
        assert "command-lint.txt" in message
        assert "pytest tests/" in message
        assert "ruff check src/" in message
        assert "edison evidence capture" in message

    def test_skips_placeholder_commands(self, tmp_path: Path) -> None:
        """Skips placeholder commands like <test-command>."""
        from edison.core.tdd.ready_gate import (
            CommandEvidenceError,
            format_evidence_error_message,
        )

        round_dir = tmp_path / "round-1"
        errors = [
            CommandEvidenceError(
                filename="command-test.txt",
                message="Missing evidence file",
                command_name="test",
                configured_command="<test-command>",
            ),
        ]

        message = format_evidence_error_message(
            task_id="task-001",
            round_num=1,
            round_dir=round_dir,
            errors=errors,
        )

        assert "<test-command>" not in message


class TestCommandEvidenceError:
    """Tests for CommandEvidenceError dataclass."""

    def test_format_actionable_with_command(self) -> None:
        """Formats with configured command."""
        from edison.core.tdd.ready_gate import CommandEvidenceError

        error = CommandEvidenceError(
            filename="command-test.txt",
            message="Missing evidence file",
            command_name="test",
            configured_command="pytest tests/",
        )

        formatted = error.format_actionable()

        assert "command-test.txt" in formatted
        assert "Missing evidence file" in formatted
        assert "pytest tests/" in formatted

    def test_format_actionable_without_command(self) -> None:
        """Formats without configured command."""
        from edison.core.tdd.ready_gate import CommandEvidenceError

        error = CommandEvidenceError(
            filename="command-test.txt",
            message="Missing evidence file",
        )

        formatted = error.format_actionable()

        assert "command-test.txt" in formatted
        assert "Missing evidence file" in formatted
        assert "Fix:" not in formatted


class TestBlockedTestTokenError:
    """Tests for BlockedTestTokenError dataclass."""

    def test_format_message(self) -> None:
        """Formats error message with location."""
        from edison.core.tdd.ready_gate import BlockedTestTokenError

        error = BlockedTestTokenError(
            file_path="tests/test_example.py",
            token=".only",
            line_number=42,
            context="Focused test will skip others",
        )

        message = error.format_message()

        assert "tests/test_example.py:42" in message
        assert ".only" in message
        assert "Focused test" in message
