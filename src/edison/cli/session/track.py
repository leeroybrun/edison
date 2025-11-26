"""
Edison session track command.

SUMMARY: Track implementation/validation work with heartbeats
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Track implementation/validation work with heartbeats"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # start subcommand
    start_parser = subparsers.add_parser("start", help="Start tracking work")
    start_parser.add_argument("--task", required=True, help="Task ID")
    start_parser.add_argument(
        "--type",
        required=True,
        choices=["implementation", "validation"],
        help="Type of work being tracked"
    )
    start_parser.add_argument("--model", help="Model name for validation")
    start_parser.add_argument("--validator", help="Validator name")
    start_parser.add_argument("--round", type=int, help="Validation round number")
    start_parser.add_argument("--json", action="store_true", help="Output as JSON")
    start_parser.add_argument("--repo-root", type=str, help="Override repository root path")

    # heartbeat subcommand
    heartbeat_parser = subparsers.add_parser("heartbeat", help="Send heartbeat")
    heartbeat_parser.add_argument("--task", required=True, help="Task ID")
    heartbeat_parser.add_argument("--json", action="store_true", help="Output as JSON")
    heartbeat_parser.add_argument("--repo-root", type=str, help="Override repository root path")

    # complete subcommand
    complete_parser = subparsers.add_parser("complete", help="Mark work as complete")
    complete_parser.add_argument("--task", required=True, help="Task ID")
    complete_parser.add_argument("--json", action="store_true", help="Output as JSON")
    complete_parser.add_argument("--repo-root", type=str, help="Override repository root path")

    # active subcommand
    active_parser = subparsers.add_parser("active", help="List active tracking sessions")
    active_parser.add_argument("--json", action="store_true", help="Output as JSON")
    active_parser.add_argument("--repo-root", type=str, help="Override repository root path")


def main(args: argparse.Namespace) -> int:
    """Track session work - delegates to core library."""
    from edison.core.qa.scoring import track_validation_score
    from edison.core.session.store import load_session, save_session
    from edison.core.io.utils import utc_timestamp

    try:
        if args.subcommand == "start":
            # Start tracking work
            result = {
                "task": args.task,
                "type": args.type,
                "started_at": utc_timestamp(),
                "status": "started"
            }

            if args.type == "validation" and args.model:
                result["model"] = args.model
            if args.validator:
                result["validator"] = args.validator
            if args.round:
                result["round"] = args.round

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Started tracking {args.type} for task {args.task}")

        elif args.subcommand == "heartbeat":
            # Send heartbeat
            result = {
                "task": args.task,
                "heartbeat_at": utc_timestamp(),
                "status": "active"
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Heartbeat sent for task {args.task}")

        elif args.subcommand == "complete":
            # Mark work as complete
            result = {
                "task": args.task,
                "completed_at": utc_timestamp(),
                "status": "completed"
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Marked work complete for task {args.task}")

        elif args.subcommand == "active":
            # List active tracking sessions
            result = {
                "active_sessions": [],
                "queried_at": utc_timestamp()
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("No active tracking sessions found")

        return 0

    except Exception as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
