"""
Edison evidence init command.

SUMMARY: Initialize evidence directories for a task
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Initialize evidence directories for a task"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument(
        "--round",
        type=int,
        default=1,
        help="Round number to ensure (default: 1)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        task_id = str(getattr(args, "task_id"))
        round_num = int(getattr(args, "round", 1) or 1)

        from edison.core.qa.evidence.service import EvidenceService

        svc = EvidenceService(task_id, project_root=project_root)
        round_dir = svc.ensure_round(round_num)
        svc.update_metadata(round_num)

        # Ensure an implementation report exists (do not create placeholder command evidence).
        try:
            existing = svc.read_implementation_report(round_num)
        except Exception:
            existing = {}
        if not existing:
            svc.write_implementation_report(
                {
                    "taskId": task_id,
                    "round": int(round_num),
                    "completionStatus": "partial",
                    "followUpTasks": [],
                    "notesForValidator": "",
                },
                round_num=round_num,
            )

        payload = {
            "taskId": task_id,
            "round": round_num,
            "evidenceRoot": str(svc.get_evidence_root().resolve()),
            "roundDir": str(round_dir.resolve()),
        }
        formatter.json_output(payload) if formatter.json_mode else formatter.text(
            f"Initialized evidence for {task_id} (round-{round_num}) at {round_dir}"
        )
        return 0

    except Exception as e:
        formatter.error(e, error_code="evidence_init_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
