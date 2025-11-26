"""
Edison qa new command.

SUMMARY: Create new QA brief for a task
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Create new QA brief for a task"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--owner",
        type=str,
        default="_unassigned_",
        help="Validator owner (default: _unassigned_)",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: create new round)",
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
    """Create QA brief - delegates to QA library."""
    from edison.core.qa import evidence, rounds
    from edison.core.paths import resolve_project_root
    from edison.core.file_io.utils import write_json_safe

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Determine round number
        round_num = args.round
        if round_num is None:
            round_num = rounds.next_round(args.task_id)

        # Create evidence directory
        evidence_dir = evidence.get_evidence_dir(args.task_id)
        round_dir = evidence_dir / f"round-{round_num}"
        round_dir.mkdir(parents=True, exist_ok=True)

        # Create QA brief
        qa_brief = {
            "task_id": args.task_id,
            "session_id": args.session,
            "round": round_num,
            "created_at": None,  # Will be set by actual implementation
            "status": "pending",
            "validators": [],
            "evidence": [],
        }

        brief_path = round_dir / "qa-brief.json"
        write_json_safe(brief_path, qa_brief)

        # Update metadata
        metadata_path = evidence_dir / "metadata.json"
        metadata = {
            "task_id": args.task_id,
            "currentRound": round_num,
            "round": round_num,
        }
        write_json_safe(metadata_path, metadata)

        if args.json:
            print(json.dumps({
                "qaPath": str(brief_path),
                "round": round_num,
                "owner": args.owner,
                "brief": qa_brief,
            }))
        else:
            print(f"Created QA brief for {args.task_id} round {round_num}")
            print(f"  Path: {brief_path}")

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
