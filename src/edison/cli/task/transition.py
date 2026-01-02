"""
Edison task transition command.

SUMMARY: Transition a task between states (alias of `edison task status --status`)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag

SUMMARY = "Transition a task between states"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "record_id",
        help="Task identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--to",
        dest="to",
        help="Target status/state (preferred flag name)",
    )
    parser.add_argument(
        "--status",
        dest="status",
        help="Target status/state (alias of --to; kept for consistency)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for transition (required for some guarded transitions like done→wip rollback)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force transition even when guards fail (bypasses validation/actions)",
    )
    parser.add_argument(
        "--session",
        help="Session context (enforces isolation when transitioning session-scoped records)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    # Delegate to the existing implementation; `task status` is the single source
    # of truth for task transitions (guards + actions + auditing).
    from edison.cli.task.status import main as status_main

    to = str(getattr(args, "to", "") or "").strip()
    status = str(getattr(args, "status", "") or "").strip()
    if to and status and to != status:
        from edison.cli import OutputFormatter

        OutputFormatter(json_mode=bool(getattr(args, "json", False))).error(
            ValueError("Use either --to or --status (not both)"),
            error_code="invalid_args",
        )
        return 1

    if to and not status:
        args.status = to

    if not str(getattr(args, "status", "") or "").strip():
        from edison.cli import OutputFormatter

        OutputFormatter(json_mode=bool(getattr(args, "json", False))).error(
            ValueError("--to (or --status) is required"),
            error_code="missing_status",
        )
        return 1

    # Force the record type to task: `task transition` is intentionally explicit.
    args.type = "task"
    return int(status_main(args))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

