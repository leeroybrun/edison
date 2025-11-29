"""
Edison qa validate command.

SUMMARY: Run validators against a task bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa import validator

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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run validators - delegates to QA library."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

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

        if formatter.json_mode:
            formatter.json_output(results)
        else:
            formatter.text(f"Validation roster for {args.task_id}:")
            formatter.text(f"  Always required: {len(roster.get('alwaysRequired', []))} validators")
            formatter.text(f"  Triggered blocking: {len(roster.get('triggeredBlocking', []))} validators")
            formatter.text(f"  Triggered optional: {len(roster.get('triggeredOptional', []))} validators")

        return 0

    except Exception as e:
        formatter.error(e, error_code="validate_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
