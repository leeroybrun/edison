"""
Edison git worktree-restore command.

SUMMARY: Restore archived worktree
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored without restoring it",
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
    """Restore archived worktree - delegates to worktree library."""
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
            print(json.dumps(result, indent=2))
        else:
            if args.dry_run:
                print(f"Would restore worktree:")
                print(f"  Session: {args.session_id}")
                print(f"  Path: {restored_path}")
                print(f"  Branch: {branch_name}")
            else:
                print(f"Restored worktree for session: {args.session_id}")
                print(f"  Path: {restored_path}")
                print(f"  Branch: {branch_name}")

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
