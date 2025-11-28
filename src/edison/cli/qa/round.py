"""
Edison qa round command.

SUMMARY: Manage QA rounds
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Manage QA rounds"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--task",
        dest="task_id",
        required=True,
        help="Task identifier",
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Status for the round (e.g., approved, rejected)",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Create new round",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all rounds",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="Show current round number",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Manage QA rounds - delegates to QA library."""
    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.io import write_json_atomic

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        ev_svc = EvidenceService(args.task_id, project_root=repo_root)

        # Default behavior: append a new round with given status
        if not args.new and not args.list and not args.current:
            # Append round entry to QA file
            from edison.core.utils.time import utc_timestamp
            from datetime import datetime

            # Find QA file
            qa_root = repo_root / ".project" / "qa"
            qa_file = None
            for state_dir in ["waiting", "todo", "wip", "done", "validated"]:
                potential = qa_root / state_dir / f"{args.task_id}-qa.md"
                if potential.exists():
                    qa_file = potential
                    break

            if not qa_file:
                raise FileNotFoundError(f"QA file for {args.task_id} not found")

            # Determine next round number from file content
            content = qa_file.read_text()
            import re
            round_matches = re.findall(r"## Round (\d+)", content)
            next_round = max([int(m) for m in round_matches], default=0) + 1

            # Append new round
            round_entry = f"\n## Round {next_round}\n"
            round_entry += f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n"
            round_entry += f"**Status:** {args.status or 'pending'}\n"
            round_entry += f"**Notes:** _None_\n"

            with open(qa_file, 'a') as f:
                f.write(round_entry)

            result = {
                "taskId": args.task_id,
                "round": next_round,
                "status": args.status or 'pending',
            }
            formatter.json_output(result) if formatter.json_mode else formatter.text(f"Appended round {next_round} for {args.task_id}")

        elif args.new:
            # Create new round
            round_path = ev_svc.create_next_round()
            round_num = ev_svc.get_current_round()

            # Update metadata
            evidence_dir = ev_svc.get_evidence_root()
            metadata_path = evidence_dir / "metadata.json"
            metadata = {
                "task_id": args.task_id,
                "currentRound": round_num,
                "round": round_num,
            }
            write_json_atomic(metadata_path, metadata)

            result = {
                "created": str(round_path),
                "round": round_num,
            }
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Created round {round_num} for {args.task_id}\n  Path: {round_path}"
            )

        elif args.list:
            # List all rounds
            evidence_dir = ev_svc.get_evidence_root()
            if not evidence_dir.exists():
                formatter.json_output({"rounds": []}) if formatter.json_mode else formatter.text(f"No rounds found for {args.task_id}")
                return 0

            round_dirs = sorted([
                int(p.name.split("-")[1])
                for p in evidence_dir.glob("round-*")
                if p.is_dir() and p.name.split("-")[1].isdigit()
            ])

            if formatter.json_mode:
                formatter.json_output({"rounds": round_dirs})
            else:
                if round_dirs:
                    formatter.text(f"Rounds for {args.task_id}:")
                    for r in round_dirs:
                        formatter.text(f"  - round-{r}")
                else:
                    formatter.text(f"No rounds found for {args.task_id}")

        else:
            # Default: show current round
            current = ev_svc.get_current_round()
            if formatter.json_mode:
                formatter.json_output({
                    "task_id": args.task_id,
                    "current_round": current,
                })
            else:
                if current is not None:
                    formatter.text(f"Current round for {args.task_id}: {current}")
                else:
                    formatter.text(f"No rounds found for {args.task_id}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="round_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
