"""
Edison session track command.

SUMMARY: Track implementation/validation work with heartbeats
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

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
    start_parser.add_argument("--model", help="Execution backend/model identifier")
    start_parser.add_argument("--validator", help="Validator identifier (required for validation)")
    start_parser.add_argument("--round", type=int, help="Evidence round number (optional)")
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
    complete_parser.add_argument(
        "--status",
        choices=["complete", "blocked", "partial"],
        default="complete",
        help="Implementation completion status (implementation only)",
    )
    add_json_flag(complete_parser)
    add_repo_root_flag(complete_parser)

    # active subcommand
    active_parser = subparsers.add_parser("active", help="List active tracking sessions")
    add_json_flag(active_parser)
    add_repo_root_flag(active_parser)


def main(args: argparse.Namespace) -> int:
    """Track session work - delegates to core tracking helpers."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        from edison.core.qa.evidence import tracking

        if args.subcommand == "start":
            if args.type == "implementation":
                result = tracking.start_implementation(
                    str(args.task),
                    project_root=repo_root,
                    model=getattr(args, "model", None),
                )
            else:
                if not getattr(args, "validator", None):
                    raise ValueError("--validator is required for type=validation")
                if not getattr(args, "model", None):
                    raise ValueError("--model is required for type=validation")
                result = tracking.start_validation(
                    str(args.task),
                    project_root=repo_root,
                    validator_id=str(args.validator),
                    model=str(args.model),
                    round_num=getattr(args, "round", None),
                )

            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Started {result['type']} tracking for {result['taskId']} (round {result['round']})"
            )

        elif args.subcommand == "heartbeat":
            result = tracking.heartbeat(str(args.task), project_root=repo_root)
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Heartbeat updated ({len(result['updated'])} file(s))"
            )

        elif args.subcommand == "complete":
            result = tracking.complete(
                str(args.task),
                project_root=repo_root,
                implementation_status=str(getattr(args, "status", "complete")),
            )
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Completed tracking ({len(result['updated'])} file(s))"
            )

        elif args.subcommand == "active":
            active = tracking.list_active(project_root=repo_root)
            if formatter.json_mode:
                formatter.json_output({"active": active, "count": len(active)})
            else:
                if not active:
                    formatter.text("No active tracking sessions found")
                else:
                    for it in active:
                        kind = it.get("type")
                        task_id = it.get("taskId")
                        extra = f" ({it.get('validatorId')})" if it.get("validatorId") else ""
                        formatter.text(f"- {task_id}{extra}: {kind} (round {it.get('round')})")

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
