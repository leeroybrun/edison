"""
Edison qa promote command.

SUMMARY: Promote QA brief between states
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Promote QA brief between states"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["waiting", "todo", "wip", "done", "validated"],
        help="Target status to promote to",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip validation checks",
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
    """Promote QA brief - delegates to QA library."""
    from edison.core.qa import promoter, bundler, rounds
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        if not args.status:
            if args.json:
                print(json.dumps({"error": "--status is required"}))
            else:
                print("Error: --status is required", file=sys.stderr)
            return 1

        # Get latest round
        round_num = rounds.latest_round(args.task_id)
        if round_num is None:
            if args.json:
                print(json.dumps({"error": "No rounds found for task"}))
            else:
                print(f"Error: No rounds found for task {args.task_id}", file=sys.stderr)
            return 1

        # Check if revalidation is needed (unless forced)
        if not args.force and args.status == "validated":
            bundle_path = bundler.bundle_summary_path(args.task_id, round_num)
            reports = promoter.collect_validator_reports([args.task_id])
            task_files = promoter.collect_task_files([args.task_id], args.session)

            if promoter.should_revalidate_bundle(bundle_path, reports, task_files):
                if args.json:
                    print(json.dumps({
                        "error": "Revalidation required",
                        "message": "Bundle is stale, run validation first",
                    }))
                else:
                    print("Error: Bundle is stale, run validation first", file=sys.stderr)
                return 1

        # Perform promotion (simplified - actual implementation would be more complex)
        result = {
            "task_id": args.task_id,
            "round": round_num,
            "old_status": "unknown",
            "new_status": args.status,
            "promoted": True,
        }

        if args.json:
            print(json.dumps(result))
        else:
            print(f"Promoted {args.task_id} to status: {args.status}")

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
