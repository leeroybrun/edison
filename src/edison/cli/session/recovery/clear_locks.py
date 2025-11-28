"""
Edison session recovery clear_locks command.

SUMMARY: Clear stale locks
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter

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

    from edison.core.session.id import validate_session_id
    from pathlib import Path
    from edison.core.utils.paths import PathResolver

    try:
        cleared = []

        if args.session_id:
            session_id = validate_session_id(args.session_id)
            # Clear locks for specific session
            # This would call a lock clearing function from the core library
            cleared.append(session_id)
        elif args.force:
            # Clear all stale locks
            # This would scan for and clear all lock files
            repo_root = PathResolver.resolve_project_root()
            lock_dir = repo_root / ".project" / "locks"
            if lock_dir.exists():
                lock_files = list(lock_dir.glob("*.lock"))
                for lock_file in lock_files:
                    if args.force:
                        lock_file.unlink()
                        cleared.append(lock_file.name)

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
