"""
Edison git worktree-restore command.

SUMMARY: Restore archived worktree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag

SUMMARY = "Restore archived worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to restore worktree for",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Override source archive path",
    )
    parser.add_argument(
        "--base-branch",
        type=str,
        help="Base branch to use (default: main)",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Restore archived worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import worktree

    try:
        # Restore the worktree from archive
        restored_path = worktree.restore_worktree(
            session_id=args.session_id,
            base_branch=args.base_branch,
            dry_run=args.dry_run,
        )

        _, branch_name = worktree.resolve_worktree_target(args.session_id)

        result = {
            "session_id": args.session_id,
            "restored_path": str(restored_path),
            "branch_name": branch_name,
            "dry_run": args.dry_run,
        }

        if args.json:
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Would restore worktree:")
                formatter.text(f"  Session: {args.session_id}")
                formatter.text(f"  Path: {restored_path}")
                formatter.text(f"  Branch: {branch_name}")
            else:
                formatter.text(f"Restored worktree for session: {args.session_id}")
                formatter.text(f"  Path: {restored_path}")
                formatter.text(f"  Branch: {branch_name}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_restore_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
