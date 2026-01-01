"""TDD readiness gates for task transitions.

This module provides validation functions that enforce TDD practices:
- Command evidence must exist with exitCode == 0
- No blocked test tokens (.only, .skip, etc.)
- Proper RED -> GREEN -> REFACTOR flow

These gates are designed to FAIL-CLOSED: any issue blocks the transition.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edison.core.qa.evidence.command_evidence import (
    parse_command_evidence,
    validate_command_evidence,
    validate_command_evidence_files,
)


@dataclass(frozen=True, slots=True)
class CommandEvidenceError:
    """Error from command evidence validation."""

    filename: str
    message: str
    command_name: str | None = None
    configured_command: str | None = None

    def format_actionable(self) -> str:
        """Format error with actionable fix commands."""
        lines = [f"  - {self.filename}: {self.message}"]
        if self.configured_command:
            lines.append(f"    Fix: {self.configured_command}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class BlockedTestTokenError:
    """Error from blocked test token detection."""

    file_path: str
    token: str
    line_number: int
    context: str

    def format_message(self) -> str:
        """Format error with file location."""
        return f"{self.file_path}:{self.line_number}: found '{self.token}' - {self.context}"


def validate_command_evidence_exit_codes(
    round_dir: Path,
    required_files: list[str],
    ci_commands: dict[str, str] | None = None,
) -> list[CommandEvidenceError]:
    """Validate all command evidence files have exitCode == 0.

    Args:
        round_dir: Path to the evidence round directory.
        required_files: List of required evidence filenames (e.g., ["command-test.txt"]).
        ci_commands: Optional mapping of command names to configured commands.
                    Used to generate actionable fix messages.

    Returns:
        List of CommandEvidenceError objects. Empty if all valid.
    """
    ci_commands = ci_commands or {}
    errors: list[CommandEvidenceError] = []

    for filename in required_files:
        file_path = round_dir / filename

        # Extract command name from filename (e.g., "command-test.txt" -> "test")
        command_name = None
        if filename.startswith("command-") and filename.endswith(".txt"):
            command_name = filename[8:-4]  # Remove "command-" prefix and ".txt" suffix

        configured_command = ci_commands.get(command_name) if command_name else None

        if not file_path.exists():
            errors.append(
                CommandEvidenceError(
                    filename=filename,
                    message="Missing evidence file",
                    command_name=command_name,
                    configured_command=configured_command,
                )
            )
            continue

        parsed = parse_command_evidence(file_path)
        if parsed is None:
            errors.append(
                CommandEvidenceError(
                    filename=filename,
                    message="Missing or malformed YAML frontmatter header (evidence v1 format required)",
                    command_name=command_name,
                    configured_command=configured_command,
                )
            )
            continue

        is_valid, error_msg = validate_command_evidence(parsed)
        if not is_valid:
            errors.append(
                CommandEvidenceError(
                    filename=filename,
                    message=error_msg or "Invalid evidence",
                    command_name=command_name,
                    configured_command=configured_command,
                )
            )

    return errors


# Common blocked test tokens that indicate incomplete/focused tests
BLOCKED_TEST_TOKENS: dict[str, str] = {
    ".only": "Focused test will skip other tests",
    ".skip": "Skipped test needs to be addressed",
    "fit(": "Focused test (Jasmine/Jest)",
    "fdescribe(": "Focused describe block (Jasmine/Jest)",
    "xit(": "Skipped test (Jasmine/Jest)",
    "xdescribe(": "Skipped describe block (Jasmine/Jest)",
    "@pytest.mark.skip": "Skipped test (pytest)",
    "@pytest.mark.only": "Focused test marker",
    "test.only(": "Focused test (Vitest/Playwright)",
    "describe.only(": "Focused describe (Vitest/Playwright)",
    "it.only(": "Focused test (Vitest/Playwright)",
}


def scan_for_blocked_test_tokens(
    files: list[Path],
    custom_tokens: dict[str, str] | None = None,
) -> list[BlockedTestTokenError]:
    """Scan files for blocked test tokens (.only, .skip, etc.).

    Args:
        files: List of file paths to scan.
        custom_tokens: Optional additional tokens to check (token -> description).

    Returns:
        List of BlockedTestTokenError objects. Empty if none found.
    """
    tokens_to_check = dict(BLOCKED_TEST_TOKENS)
    if custom_tokens:
        tokens_to_check.update(custom_tokens)

    errors: list[BlockedTestTokenError] = []

    for file_path in files:
        if not file_path.exists() or not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for token, description in tokens_to_check.items():
                if token in line:
                    errors.append(
                        BlockedTestTokenError(
                            file_path=str(file_path),
                            token=token,
                            line_number=line_num,
                            context=description,
                        )
                    )

    return errors


def format_evidence_error_message(
    task_id: str,
    round_num: int,
    round_dir: Path,
    errors: list[CommandEvidenceError],
    ci_commands: dict[str, str] | None = None,
) -> str:
    """Format a comprehensive, actionable error message for evidence failures.

    Args:
        task_id: Task identifier.
        round_num: Current round number.
        round_dir: Path to the evidence round directory.
        errors: List of CommandEvidenceError objects.
        ci_commands: Optional mapping of command names to configured commands.

    Returns:
        Formatted error message with actionable fix instructions.
    """
    ci_commands = ci_commands or {}

    lines = [
        f"Evidence validation failed for task '{task_id}' (round-{round_num}):",
        f"Evidence directory: {round_dir}",
        "",
        "Issues found:",
    ]

    for error in errors:
        lines.append(f"  - {error.filename}: {error.message}")
        cmd = error.configured_command or ci_commands.get(error.command_name or "")
        if cmd and not cmd.startswith("<"):  # Skip placeholder commands
            lines.append(f"    Run: {cmd}")

    lines.extend([
        "",
        "Fix instructions:",
        "  1. Run the failing commands and capture output with proper evidence format",
        "  2. Ensure each command succeeds (exit code 0)",
        "  3. Use `edison evidence capture <task>` to automatically capture evidence",
    ])

    return "\n".join(lines)


__all__ = [
    "CommandEvidenceError",
    "BlockedTestTokenError",
    "validate_command_evidence_exit_codes",
    "scan_for_blocked_test_tokens",
    "format_evidence_error_message",
    "BLOCKED_TEST_TOKENS",
]
