"""
Edison evidence capture command.

SUMMARY: Run CI commands and capture output as evidence
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Run CI commands and capture output as evidence"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier (e.g., test-task-123)",
    )
    parser.add_argument(
        "--command",
        dest="command_name",
        help="Run only specified command (e.g., lint, test)",
    )
    parser.add_argument(
        "--continue",
        dest="continue_on_failure",
        action="store_true",
        help="Continue running commands after failure",
    )
    parser.add_argument(
        "--round",
        type=int,
        dest="round_num",
        help="Explicit round number (default: latest)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _load_ci_commands(project_root: Path) -> dict[str, str]:
    """Load CI commands from configuration."""
    from edison.core.config.domains.ci import CIConfig

    ci_config = CIConfig(repo_root=project_root)
    return ci_config.commands


def _run_command(
    command: str,
    cwd: Path,
    pipefail: bool = True,
) -> tuple[int, str, datetime, datetime]:
    """Run a shell command and capture output.

    Args:
        command: Shell command to run
        cwd: Working directory
        pipefail: If True, enable pipefail mode so piped commands fail correctly

    Returns:
        Tuple of (exit_code, output, started_at, completed_at)
    """
    started_at = datetime.now(tz=timezone.utc)

    # Wrap command with pipefail if enabled
    if pipefail:
        wrapped_command = f"set -o pipefail; {command}"
    else:
        wrapped_command = command

    try:
        result = subprocess.run(
            wrapped_command,
            shell=True,
            executable="/bin/bash",
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=None,  # Use current environment
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
    except Exception as e:
        exit_code = 1
        output = str(e)

    completed_at = datetime.now(tz=timezone.utc)
    return exit_code, output, started_at, completed_at


def main(args: argparse.Namespace) -> int:
    """Run CI commands and capture output as evidence."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        task_id = str(args.task_id)
        specific_command = getattr(args, "command_name", None)
        continue_on_failure = getattr(args, "continue_on_failure", False)
        round_num = getattr(args, "round_num", None)

        # Import evidence utilities
        from edison.core.qa.evidence import EvidenceService
        from edison.core.qa.evidence.command_evidence import write_command_evidence

        service = EvidenceService(task_id=task_id, project_root=project_root)

        # Get round directory
        if round_num is not None:
            round_dir = service.get_round_dir(round_num)
            if not round_dir.exists():
                raise RuntimeError(f"Round {round_num} does not exist")
        else:
            round_dir = service.get_current_round_dir()
            if round_dir is None:
                raise RuntimeError("No evidence round exists. Run 'evidence init' first.")
            from edison.core.qa.evidence import rounds
            round_num = rounds.get_round_number(round_dir)

        # Load CI commands
        ci_commands = _load_ci_commands(project_root)
        if not ci_commands:
            raise RuntimeError("No CI commands configured in ci.yaml")

        # Filter to specific command if requested
        if specific_command:
            if specific_command not in ci_commands:
                raise RuntimeError(f"Command '{specific_command}' not found in ci.yaml")
            ci_commands = {specific_command: ci_commands[specific_command]}

        # Load evidence file mapping from QA config
        from edison.core.config.domains.qa import QAConfig

        qa_config = QAConfig(repo_root=project_root)
        evidence_files = qa_config.validation_config.get("evidence", {}).get("files", {}) or {}

        # Run each command and capture output
        results: list[dict[str, Any]] = []
        passed = 0
        failed = 0

        for cmd_name, cmd_string in ci_commands.items():
            # Determine output filename
            filename = evidence_files.get(cmd_name, f"command-{cmd_name}.txt")

            # Run command
            exit_code, output, started_at, completed_at = _run_command(
                cmd_string,
                project_root,
            )

            # Write evidence file
            evidence_path = round_dir / filename
            write_command_evidence(
                path=evidence_path,
                task_id=task_id,
                round_num=round_num,
                command_name=cmd_name,
                command=cmd_string,
                cwd=str(project_root),
                exit_code=exit_code,
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                shell="bash",
                pipefail=True,
            )

            result = {
                "name": cmd_name,
                "command": cmd_string,
                "exitCode": exit_code,
                "file": filename,
            }
            results.append(result)

            if exit_code == 0:
                passed += 1
            else:
                failed += 1
                if not continue_on_failure:
                    break

        if formatter.json_mode:
            formatter.json_output({
                "taskId": task_id,
                "round": round_num,
                "commands": results,
                "passed": passed,
                "failed": failed,
            })
        else:
            formatter.text(f"Captured {len(results)} commands: {passed} passed, {failed} failed")

        return 0 if failed == 0 or continue_on_failure else 1

    except Exception as e:
        formatter.error(e, error_code="evidence_capture_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
