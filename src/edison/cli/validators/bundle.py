"""
Edison validators bundle command.

SUMMARY: Bundle validator results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Bundle validator results"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier to bundle results for",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: latest round)",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve the bundle (mark as passed)",
    )
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Reject the bundle (mark as failed)",
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
    """Bundle validator results - delegates to bundler library."""
    from edison.core.qa import bundler, rounds
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Determine round number
        if args.round:
            round_num = args.round
        else:
            latest = rounds.latest_round(args.task_id)
            if latest is None:
                raise ValueError(f"No validation rounds found for task {args.task_id}")
            round_num = latest

        # Load existing bundle summary
        summary = bundler.load_bundle_summary(args.task_id, round_num)

        # Update approval status if requested
        if args.approve and args.reject:
            raise ValueError("Cannot both approve and reject a bundle")

        if args.approve:
            summary["approved"] = True
            summary["status"] = "passed"
            bundler.write_bundle_summary(args.task_id, round_num, summary)
            message = f"Bundle approved for task {args.task_id}, round {round_num}"
        elif args.reject:
            summary["approved"] = False
            summary["status"] = "failed"
            bundler.write_bundle_summary(args.task_id, round_num, summary)
            message = f"Bundle rejected for task {args.task_id}, round {round_num}"
        else:
            message = f"Bundle summary for task {args.task_id}, round {round_num}"

        result = {
            "task_id": args.task_id,
            "round": round_num,
            "summary": summary,
            "message": message,
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(message)
            if summary:
                print(f"  Status: {summary.get('status', 'unknown')}")
                print(f"  Approved: {summary.get('approved', False)}")

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
