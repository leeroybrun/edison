"""
Edison git worktree-archive command.

SUMMARY: Archive session worktree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag

SUMMARY = "Archive session worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to archive worktree for",
    )
    parser.add_argument(
        "--destination",
        type=str,
        help="Override archive destination path",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Archive git worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import worktree

    try:
        # Resolve the worktree path for this session
        worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

        if not worktree_path.exists():
            if args.json:
                formatter.json_output({"error": "Worktree not found", "path": str(worktree_path)})
            else:
                formatter.error(f"Worktree not found: {worktree_path}", error_code="worktree_not_found")
            return 1

        # Archive the worktree
        archived_path = worktree.archive_worktree(
            session_id=args.session_id,
            worktree_path=worktree_path,
            dry_run=args.dry_run,
        )

        result = {
            "session_id": args.session_id,
            "source_path": str(worktree_path),
            "archived_path": str(archived_path),
            "branch_name": branch_name,
            "dry_run": args.dry_run,
        }

        if args.json:
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Would archive worktree:")
                formatter.text(f"  From: {worktree_path}")
                formatter.text(f"  To: {archived_path}")
            else:
                formatter.text(f"Archived worktree for session: {args.session_id}")
                formatter.text(f"  From: {worktree_path}")
                formatter.text(f"  To: {archived_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_archive_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
