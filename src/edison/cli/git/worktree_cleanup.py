"""
Edison git worktree-cleanup command.

SUMMARY: Clean up session worktree
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Clean up session worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to cleanup worktree for",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force cleanup even if worktree has uncommitted changes",
    )
    parser.add_argument(
        "--delete-branch",
        action="store_true",
        help="Also delete the session branch",
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
    """Cleanup git worktree - delegates to worktree library."""
    from edison.core.session import worktree

    try:
        # Resolve the worktree path and branch name for this session
        worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

        if not worktree_path.exists():
            if args.json:
                print(json.dumps({"error": "Worktree not found", "path": str(worktree_path)}))
            else:
                print(f"Worktree not found: {worktree_path}", file=sys.stderr)
            return 1

        # Cleanup the worktree
        worktree.cleanup_worktree(
            session_id=args.session_id,
            worktree_path=worktree_path,
            branch_name=branch_name,
            delete_branch=args.delete_branch,
        )

        result = {
            "session_id": args.session_id,
            "worktree_path": str(worktree_path),
            "branch_name": branch_name,
            "deleted_branch": args.delete_branch,
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cleaned up worktree for session: {args.session_id}")
            print(f"  Path: {worktree_path}")
            if args.delete_branch:
                print(f"  Deleted branch: {branch_name}")

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
