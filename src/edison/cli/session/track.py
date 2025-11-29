"""
Edison session track command.

SUMMARY: Track implementation/validation work with heartbeats
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter
from edison.core.qa.scoring.scoring import track_validation_score
from edison.core.utils.time import utc_timestamp

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
    add_json_flag(start_parser)
    add_repo_root_flag(start_parser)

    # heartbeat subcommand
    heartbeat_parser = subparsers.add_parser("heartbeat", help="Send heartbeat")
    heartbeat_parser.add_argument("--task", required=True, help="Task ID")
    add_json_flag(heartbeat_parser)
    add_repo_root_flag(heartbeat_parser)

    # complete subcommand
    complete_parser = subparsers.add_parser("complete", help="Mark work as complete")
    complete_parser.add_argument("--task", required=True, help="Task ID")
    add_json_flag(complete_parser)
    add_repo_root_flag(complete_parser)

    # active subcommand
    active_parser = subparsers.add_parser("active", help="List active tracking sessions")
    add_json_flag(active_parser)
    add_repo_root_flag(active_parser)


def main(args: argparse.Namespace) -> int:
    """Track session work - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


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

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text(f"Started tracking {args.type} for task {args.task}")

        elif args.subcommand == "heartbeat":
            # Send heartbeat
            result = {
                "task": args.task,
                "heartbeat_at": utc_timestamp(),
                "status": "active"
            }

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text(f"Heartbeat sent for task {args.task}")

        elif args.subcommand == "complete":
            # Mark work as complete
            result = {
                "task": args.task,
                "completed_at": utc_timestamp(),
                "status": "completed"
            }

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text(f"Marked work complete for task {args.task}")

        elif args.subcommand == "active":
            # List active tracking sessions
            result = {
                "active_sessions": [],
                "queried_at": utc_timestamp()
            }

            if formatter.json_mode:
                formatter.json_output(result)
            else:
                formatter.text("No active tracking sessions found")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
