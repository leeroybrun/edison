"""
Edison session recovery clear_locks command.

SUMMARY: Clear stale locks
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Clear stale locks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session-id",
        type=str,
        help="Clear locks for specific session",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force clear all locks",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Clear stale locks - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.lifecycle.recovery import clear_session_locks, clear_all_locks

    try:
        if args.session_id:
            # Clear locks for specific session
            cleared = clear_session_locks(args.session_id)
        elif args.force:
            # Clear all stale locks
            cleared = clear_all_locks(force=True)
        else:
            cleared = []

        result = {
            "cleared_locks": cleared,
            "count": len(cleared),
            "status": "completed"
        }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if cleared:
                formatter.text(f"✓ Cleared {len(cleared)} stale lock(s)")
                for lock in cleared:
                    formatter.text(f"  - {lock}")
            else:
                formatter.text("No stale locks found")

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
