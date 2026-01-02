"""
Edison evidence init command.

SUMMARY: Initialize evidence round directory
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Initialize evidence round directory"


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
        help="Explicit round number (default: next available)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Initialize evidence round directory with implementation report stub."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        task_id = str(args.task_id)
        round_num = getattr(args, "round_num", None)

        # Import evidence service
        from edison.core.qa.evidence import EvidenceService

        service = EvidenceService(task_id=task_id, project_root=project_root)

        # Ensure round directory exists
        if round_num is not None:
            round_dir = service.ensure_round(round_num)
        else:
            # Get current round or create round-1
            current = service.get_current_round()
            if current is None:
                round_dir = service.ensure_round(1)
                round_num = 1
            else:
                round_dir = service.get_round_dir(current)
                round_num = current

        if round_num is None:
            from edison.core.qa.evidence import rounds
            round_num = rounds.get_round_number(round_dir)

        # Check for existing implementation report
        report_path = round_dir / service.implementation_filename
        if report_path.exists():
            # Idempotent: don't overwrite existing report
            if formatter.json_mode:
                formatter.json_output({
                    "status": "exists",
                    "round": round_num,
                    "evidencePath": str(round_dir),
                    "reportPath": str(report_path),
                })
            else:
                formatter.text(f"Evidence round {round_num} already initialized: {round_dir}")
            return 0

        # Create implementation report stub with required schema fields
        import os
        import socket

        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        frontmatter = {
            "taskId": task_id,
            "round": round_num,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "claude",
            "completionStatus": "partial",
            "followUpTasks": [],
            "notesForValidator": "",
            "tracking": {
                "processId": os.getpid(),
                "hostname": socket.gethostname(),
                "startedAt": now,
            },
        }

        # Build report content
        yaml_content = yaml.safe_dump(
            frontmatter,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        content = f"---\n{yaml_content}---\n\n# Implementation Report\n\n"

        # Write stub
        report_path.write_text(content, encoding="utf-8")

        if formatter.json_mode:
            formatter.json_output({
                "status": "created",
                "round": round_num,
                "evidencePath": str(round_dir),
                "reportPath": str(report_path),
            })
        else:
            formatter.text(f"Initialized evidence round {round_num}: {round_dir}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="evidence_init_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
