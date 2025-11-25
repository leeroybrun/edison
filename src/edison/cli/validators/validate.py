"""
Edison validators validate command.

SUMMARY: Run validators on task/changes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Run validators on task/changes"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier to validate",
    )
    parser.add_argument(
        "--validators",
        nargs="+",
        help="Specific validator IDs to run (default: run all applicable)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all validators (including non-triggered)",
    )
    parser.add_argument(
        "--blocking-only",
        action="store_true",
        help="Only run blocking validators",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID context (optional)",
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
    """Run validators - delegates to validation library."""
    from edison.core.qa import validator, rounds
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Determine round number
        round_num = args.round if args.round else rounds.next_round(args.task_id)

        # Build validator roster
        roster = validator.build_validator_roster(
            args.task_id,
            session_id=args.session,
        )

        if "error" in roster:
            raise RuntimeError(roster["error"])

        # Filter validators based on flags
        if args.blocking_only:
            roster["triggeredOptional"] = []

        if args.validators:
            # Filter to specific validators
            roster = {
                "alwaysRequired": [
                    v for v in roster.get("alwaysRequired", [])
                    if v["id"] in args.validators
                ],
                "triggeredBlocking": [
                    v for v in roster.get("triggeredBlocking", [])
                    if v["id"] in args.validators
                ],
                "triggeredOptional": [
                    v for v in roster.get("triggeredOptional", [])
                    if v["id"] in args.validators
                ],
            }

        # Calculate total validators
        total = (
            len(roster.get("alwaysRequired", [])) +
            len(roster.get("triggeredBlocking", [])) +
            len(roster.get("triggeredOptional", []))
        )

        result = {
            "task_id": args.task_id,
            "session_id": args.session,
            "round": round_num,
            "roster": roster,
            "total_validators": total,
            "status": "ready",
            "message": f"Ready to run {total} validators for round {round_num}",
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Validation roster for {args.task_id} (round {round_num}):")
            print(f"  Always required: {len(roster.get('alwaysRequired', []))} validators")
            print(f"  Triggered blocking: {len(roster.get('triggeredBlocking', []))} validators")
            print(f"  Triggered optional: {len(roster.get('triggeredOptional', []))} validators")
            print(f"  Total: {total} validators")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
