"""
Edison git worktree-list command.

SUMMARY: List all git worktrees
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "List all git worktrees"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session",
        type=str,
        help="Filter to specific session worktree",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include archived worktrees",
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
    """List git worktrees - delegates to worktree library."""
    from edison.core.session import worktree

    try:
        # Get list of active worktrees
        worktrees = worktree.list_worktrees()

        # Format as list of dicts
        worktree_list = [
            {
                "path": str(path),
                "branch": branch,
                "exists": path.exists(),
            }
            for path, branch in worktrees
        ]

        # Filter by session if requested
        if args.session:
            _, session_branch = worktree.resolve_worktree_target(args.session)
            worktree_list = [
                wt for wt in worktree_list if wt["branch"] == session_branch
            ]

        # Add archived worktrees if requested
        archived = []
        if args.all:
            archived_paths = worktree.list_archived_worktrees_sorted()
            archived = [
                {
                    "path": str(path),
                    "branch": "archived",
                    "exists": path.exists(),
                    "archived": True,
                }
                for path in archived_paths
            ]

        result = {
            "worktrees": worktree_list,
            "archived": archived,
            "total": len(worktree_list),
            "total_archived": len(archived),
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if worktree_list:
                print(f"Active worktrees ({len(worktree_list)}):")
                for wt in worktree_list:
                    status = "✓" if wt["exists"] else "✗"
                    print(f"  {status} {wt['branch']}")
                    print(f"     {wt['path']}")
            else:
                print("No active worktrees found")

            if archived:
                print(f"\nArchived worktrees ({len(archived)}):")
                for wt in archived:
                    status = "✓" if wt["exists"] else "✗"
                    print(f"  {status} {Path(wt['path']).name}")
                    print(f"     {wt['path']}")

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
