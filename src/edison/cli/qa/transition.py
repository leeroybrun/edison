"""
Edison qa transition command.

SUMMARY: Transition a QA brief between states (alias of `edison qa promote`)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter

SUMMARY = "Transition a QA brief between states"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "task_id",
        help="Task identifier (or QA id ending with -qa/.qa)",
    )
    parser.add_argument(
        "--to",
        dest="to",
        help="Target QA status/state (preferred flag name)",
    )
    parser.add_argument(
        "--status",
        dest="status",
        help="Target QA status/state (alias of --to; kept for consistency)",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    from edison.cli.qa.promote import main as promote_main

    to = str(getattr(args, "to", "") or "").strip()
    status = str(getattr(args, "status", "") or "").strip()
    if to and status and to != status:
        OutputFormatter(json_mode=bool(getattr(args, "json", False))).error(
            ValueError("Use either --to or --status (not both)"),
            error_code="invalid_args",
        )
        return 1

    if to and not status:
        args.status = to

    if not str(getattr(args, "status", "") or "").strip():
        OutputFormatter(json_mode=bool(getattr(args, "json", False))).error(
            ValueError("--to (or --status) is required"),
            error_code="missing_status",
        )
        return 1

    return int(promote_main(args))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

