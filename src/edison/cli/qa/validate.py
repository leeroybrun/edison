"""
Edison qa validate command.

SUMMARY: Run validators against a task bundle
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Run validators against a task bundle"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier to validate",
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
        "--validators",
        nargs="+",
        help="Specific validator IDs to run (default: run all applicable)",
    )
    parser.add_argument(
        "--blocking-only",
        action="store_true",
        help="Only run blocking validators",
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
    """Run validators - delegates to QA library."""
    from edison.core.qa import validator
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Build validator roster
        roster = validator.build_validator_roster(
            args.task_id,
            session_id=args.session,
        )

        if args.blocking_only:
            # Filter to only blocking validators
            roster["triggeredOptional"] = []

        # Filter to specific validators if requested
        if args.validators:
            all_validators = (
                roster.get("alwaysRequired", []) +
                roster.get("triggeredBlocking", []) +
                roster.get("triggeredOptional", [])
            )
            roster = {
                "alwaysRequired": [v for v in roster.get("alwaysRequired", []) if v["id"] in args.validators],
                "triggeredBlocking": [v for v in roster.get("triggeredBlocking", []) if v["id"] in args.validators],
                "triggeredOptional": [v for v in roster.get("triggeredOptional", []) if v["id"] in args.validators],
            }

        results = {
            "task_id": args.task_id,
            "session_id": args.session,
            "roster": roster,
            "status": "pending",
        }

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Validation roster for {args.task_id}:")
            print(f"  Always required: {len(roster.get('alwaysRequired', []))} validators")
            print(f"  Triggered blocking: {len(roster.get('triggeredBlocking', []))} validators")
            print(f"  Triggered optional: {len(roster.get('triggeredOptional', []))} validators")

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
