"""
Edison git worktree-archive command.

SUMMARY: Archive session worktree
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without archiving it",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Archive git worktree - delegates to worktree library."""
    from edison.core.session import worktree

    try:
        # Resolve the worktree path for this session
        worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

        if not worktree_path.exists():
            if args.json:
                print(json.dumps({"error": "Worktree not found", "path": str(worktree_path)}))
            else:
                print(f"Worktree not found: {worktree_path}", file=sys.stderr)
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
            print(json.dumps(result, indent=2))
        else:
            if args.dry_run:
                print(f"Would archive worktree:")
                print(f"  From: {worktree_path}")
                print(f"  To: {archived_path}")
            else:
                print(f"Archived worktree for session: {args.session_id}")
                print(f"  From: {worktree_path}")
                print(f"  To: {archived_path}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
