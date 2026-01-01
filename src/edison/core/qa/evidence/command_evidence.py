"""Command Evidence v1 Format - Write, Parse, and Validate.

This module provides the canonical format for command evidence files.
Each command-*.txt file contains YAML frontmatter with metadata followed
by the raw command output.

Evidence Format v1:
---
evidenceVersion: 1
evidenceKind: "command"
taskId: "<task-id>"
round: 1
commandName: "type-check"
command: "<exact command string>"
cwd: "<absolute path>"
shell: "bash"
pipefail: true
startedAt: "2025-12-31T16:33:50Z"
completedAt: "2025-12-31T16:34:12Z"
exitCode: 0
---
<raw combined output>
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Required keys in command evidence v1 frontmatter
REQUIRED_KEYS_V1: frozenset[str] = frozenset({
    "evidenceVersion",
    "evidenceKind",
    "taskId",
    "round",
    "commandName",
    "command",
    "cwd",
    "exitCode",
})

# Pattern to extract YAML frontmatter from evidence files
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?(.*)",
    re.DOTALL,
)


def parse_command_evidence(path: Path) -> dict[str, Any] | None:
    """Parse command evidence v1 file and return frontmatter + output.

    Args:
        path: Path to the evidence file.

    Returns:
        Dictionary with frontmatter keys plus 'output' key,
        or None if file doesn't exist, lacks frontmatter, or is malformed.
    """
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None

    frontmatter_text = match.group(1)
    output_text = match.group(2) if match.group(2) else ""

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None

    if not isinstance(frontmatter, dict):
        return None

    # Validate required keys
    for key in REQUIRED_KEYS_V1:
        if key not in frontmatter:
            return None

    # Add the output section
    frontmatter["output"] = output_text

    return frontmatter


def validate_command_evidence(
    parsed: dict[str, Any],
) -> tuple[bool, str | None]:
    """Validate parsed command evidence for success criteria.

    Args:
        parsed: Parsed evidence dictionary from parse_command_evidence().

    Returns:
        Tuple of (is_valid, error_message).
        is_valid is True if exitCode == 0.
        error_message is None if valid, or describes the failure.
    """
    exit_code = parsed.get("exitCode")

    if exit_code is None:
        return False, "Missing exitCode in evidence frontmatter"

    if exit_code != 0:
        command_name = parsed.get("commandName", "unknown")
        command = parsed.get("command", "")
        return False, (
            f"Command '{command_name}' failed with exit code {exit_code}. "
            f"Command: {command}"
        )

    return True, None


def validate_command_evidence_files(
    round_dir: Path,
    required_files: list[str],
) -> list[str]:
    """Validate multiple command evidence files in a round directory.

    Args:
        round_dir: Path to the round directory (e.g., round-1/).
        required_files: List of required evidence filenames.

    Returns:
        List of error messages. Empty list if all files are valid.
    """
    errors: list[str] = []

    for filename in required_files:
        file_path = round_dir / filename

        if not file_path.exists():
            errors.append(f"Missing evidence file: {filename}")
            continue

        parsed = parse_command_evidence(file_path)
        if parsed is None:
            errors.append(
                f"Invalid evidence file '{filename}': "
                "missing or malformed YAML frontmatter header"
            )
            continue

        is_valid, error = validate_command_evidence(parsed)
        if not is_valid:
            errors.append(f"Evidence file '{filename}': {error}")

    return errors


def write_command_evidence(
    path: Path,
    task_id: str,
    round_num: int,
    command_name: str,
    command: str,
    cwd: str,
    exit_code: int,
    output: str,
    started_at: datetime,
    completed_at: datetime,
    shell: str = "bash",
    pipefail: bool = True,
) -> None:
    """Write command evidence v1 file with YAML frontmatter.

    Args:
        path: Path where to write the evidence file.
        task_id: Task identifier.
        round_num: Evidence round number.
        command_name: Short name (e.g., 'test', 'lint', 'build').
        command: Full command string that was executed.
        cwd: Working directory where command was run.
        exit_code: Command exit code (0 = success).
        output: Combined stdout+stderr output.
        started_at: When command started.
        completed_at: When command completed.
        shell: Shell used (default: bash).
        pipefail: Whether pipefail was enabled (default: True).
    """
    # Ensure started_at and completed_at are timezone-aware
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    frontmatter = {
        "evidenceVersion": 1,
        "evidenceKind": "command",
        "taskId": task_id,
        "round": round_num,
        "commandName": command_name,
        "command": command,
        "cwd": cwd,
        "shell": shell,
        "pipefail": pipefail,
        "startedAt": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completedAt": completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exitCode": exit_code,
    }

    # Build the file content
    yaml_content = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    # Ensure output ends with newline if not empty
    if output and not output.endswith("\n"):
        output = output + "\n"

    content = f"---\n{yaml_content}---\n{output}"

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(content, encoding="utf-8")


__all__ = [
    "REQUIRED_KEYS_V1",
    "parse_command_evidence",
    "validate_command_evidence",
    "validate_command_evidence_files",
    "write_command_evidence",
]
