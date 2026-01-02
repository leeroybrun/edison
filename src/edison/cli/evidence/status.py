"""
Edison evidence status command.

SUMMARY: Check evidence completeness and command success
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Check evidence completeness and command success"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier (e.g., test-task-123)",
    )
    parser.add_argument(
        "--round",
        type=int,
        dest="round_num",
        help="Explicit round number (default: latest)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Check evidence completeness and command success."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        task_id = str(args.task_id)
        round_num = getattr(args, "round_num", None)

        # Import evidence utilities
        from edison.core.qa.evidence import EvidenceService
        from edison.core.qa.evidence import rounds
        from edison.core.qa.evidence.command_evidence import parse_command_evidence

        service = EvidenceService(task_id=task_id, project_root=project_root)

        # Get round directory
        round_dir: Path
        if round_num is not None:
            round_dir = service.get_round_dir(round_num)
            if not round_dir.exists():
                raise RuntimeError(f"Round {round_num} does not exist")
        else:
            maybe_round_dir = service.get_current_round_dir()
            if maybe_round_dir is None:
                raise RuntimeError("No evidence round exists. Run 'evidence init' first.")
            round_dir = maybe_round_dir
            round_num = rounds.get_round_number(round_dir)

        # Load required evidence files from QA config
        from edison.core.config.domains.qa import QAConfig

        qa_config = QAConfig(repo_root=project_root)
        required_files = qa_config.get_required_evidence_files()

        # Check each required file
        present: list[str] = []
        missing: list[str] = []
        failed: list[dict[str, Any]] = []

        for filename in required_files:
            file_path = round_dir / filename
            if file_path.exists():
                present.append(filename)

                # Parse to check exit code
                parsed = parse_command_evidence(file_path)
                if parsed is not None:
                    exit_code = parsed.get("exitCode")
                    if exit_code is not None and exit_code != 0:
                        failed.append({
                            "file": filename,
                            "commandName": parsed.get("commandName", "unknown"),
                            "exitCode": exit_code,
                        })
            else:
                missing.append(filename)

        # Determine overall status
        all_present = len(missing) == 0
        all_passed = len(failed) == 0
        success = all_present and all_passed

        if formatter.json_mode:
            formatter.json_output({
                "taskId": task_id,
                "round": round_num,
                "present": present,
                "missing": missing,
                "failed": failed,
                "complete": all_present,
                "passed": all_passed,
            })
        else:
            # Text output
            print(f"Evidence status for {task_id} round {round_num}:")
            print()

            if present:
                print("Present files:")
                for f in present:
                    print(f"  - {f}")
                print()

            if missing:
                print("Missing files:")
                for f in missing:
                    print(f"  - {f}")
                print()

            if failed:
                print("Failed commands:")
                for fail_entry in failed:
                    print(f"  - {fail_entry['file']}: {fail_entry['commandName']} (exit code {fail_entry['exitCode']})")
                print()

            if success:
                print("All evidence present and passed.")
            else:
                if not all_present:
                    print(f"INCOMPLETE: {len(missing)} required files missing")
                if not all_passed:
                    print(f"FAILED: {len(failed)} commands failed")

        return 0 if success else 1

    except Exception as e:
        formatter.error(e, error_code="evidence_status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
