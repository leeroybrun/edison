"""
Edison qa bundle command.

SUMMARY: Create or inspect QA validation bundle
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Create or inspect QA validation bundle"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: latest round)",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create new bundle summary",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect existing bundle",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mark bundle as approved",
    )
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Mark bundle as rejected",
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
    """Bundle management - delegates to QA library."""
    from edison.core.qa import bundler, rounds
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Determine round number
        round_num = args.round
        if round_num is None:
            round_num = rounds.latest_round(args.task_id)
            if round_num is None:
                if args.json:
                    print(json.dumps({"error": "No rounds found for task"}))
                else:
                    print(f"Error: No rounds found for task {args.task_id}", file=sys.stderr)
                return 1

        # Load or create bundle
        if args.create:
            summary = {
                "task_id": args.task_id,
                "round": round_num,
                "status": "pending",
                "validators": {},
            }
            path = bundler.write_bundle_summary(args.task_id, round_num, summary)
            if args.json:
                print(json.dumps({"created": str(path), "summary": summary}))
            else:
                print(f"Created bundle: {path}")
        elif args.approve or args.reject:
            summary = bundler.load_bundle_summary(args.task_id, round_num)
            if not summary:
                if args.json:
                    print(json.dumps({"error": "Bundle not found"}))
                else:
                    print("Error: Bundle not found", file=sys.stderr)
                return 1
            summary["status"] = "approved" if args.approve else "rejected"
            path = bundler.write_bundle_summary(args.task_id, round_num, summary)
            if args.json:
                print(json.dumps({"updated": str(path), "summary": summary}))
            else:
                print(f"Updated bundle status to: {summary['status']}")
        else:
            # Default: inspect
            summary = bundler.load_bundle_summary(args.task_id, round_num)
            if args.json:
                print(json.dumps(summary if summary else {"error": "Bundle not found"}))
            else:
                if summary:
                    print(f"Bundle for {args.task_id} round {round_num}:")
                    print(f"  Status: {summary.get('status', 'unknown')}")
                    print(f"  Validators: {len(summary.get('validators', {}))}")
                else:
                    print(f"No bundle found for {args.task_id} round {round_num}")

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
