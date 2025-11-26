"""
Edison qa round command.

SUMMARY: Manage QA rounds
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Manage QA rounds - delegates to QA library."""
    from edison.core.qa import rounds, evidence
    from edison.core.paths import resolve_project_root
    from edison.core.file_io.utils import write_json_safe

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Default behavior: append a new round with given status
        if not args.new and not args.list and not args.current:
            # Append round entry to QA file
            from edison.core.file_io.utils import utc_timestamp
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

            if args.json:
                print(json.dumps({
                    "taskId": args.task_id,
                    "round": next_round,
                    "status": args.status or 'pending',
                }))
            else:
                print(f"Appended round {next_round} for {args.task_id}")

        elif args.new:
            # Create new round
            round_num = rounds.next_round(args.task_id)
            round_path = rounds.round_dir(args.task_id, round_num)
            round_path.mkdir(parents=True, exist_ok=True)

            # Update metadata
            evidence_dir = evidence.get_evidence_dir(args.task_id)
            metadata_path = evidence_dir / "metadata.json"
            metadata = {
                "task_id": args.task_id,
                "currentRound": round_num,
                "round": round_num,
            }
            write_json_safe(metadata_path, metadata)

            if args.json:
                print(json.dumps({
                    "created": str(round_path),
                    "round": round_num,
                }))
            else:
                print(f"Created round {round_num} for {args.task_id}")
                print(f"  Path: {round_path}")

        elif args.list:
            # List all rounds
            evidence_dir = evidence.get_evidence_dir(args.task_id)
            if not evidence_dir.exists():
                if args.json:
                    print(json.dumps({"rounds": []}))
                else:
                    print(f"No rounds found for {args.task_id}")
                return 0

            round_dirs = sorted([
                int(p.name.split("-")[1])
                for p in evidence_dir.glob("round-*")
                if p.is_dir() and p.name.split("-")[1].isdigit()
            ])

            if args.json:
                print(json.dumps({"rounds": round_dirs}))
            else:
                if round_dirs:
                    print(f"Rounds for {args.task_id}:")
                    for r in round_dirs:
                        print(f"  - round-{r}")
                else:
                    print(f"No rounds found for {args.task_id}")

        else:
            # Default: show current round
            current = rounds.latest_round(args.task_id)
            if args.json:
                print(json.dumps({
                    "task_id": args.task_id,
                    "current_round": current,
                }))
            else:
                if current is not None:
                    print(f"Current round for {args.task_id}: {current}")
                else:
                    print(f"No rounds found for {args.task_id}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
