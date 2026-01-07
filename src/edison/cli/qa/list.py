"""
Edison qa list command.

SUMMARY: List QA records across queues
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
)

SUMMARY = "List QA records across queues"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--status",
        help="Filter by status",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include terminal/final states (e.g., validated)",
    )
    parser.add_argument(
        "--session",
        help="Filter by session ID",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List QA records - delegates to the shared record listing implementation."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        # Delegate to the canonical list implementation used by `edison task list --type qa`.
        from edison.cli.task.list import main as task_list_main

        setattr(args, "type", "qa")
        return task_list_main(args)
    except Exception as exc:
        formatter.error(exc, error_code="qa_list_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

