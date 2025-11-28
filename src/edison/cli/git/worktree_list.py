"""
Edison git worktree-list command.

SUMMARY: List all git worktrees
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag

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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List git worktrees - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

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
            formatter.json_output(result)
        else:
            if worktree_list:
                formatter.text(f"Active worktrees ({len(worktree_list)}):")
                for wt in worktree_list:
                    status = "✓" if wt["exists"] else "✗"
                    formatter.text(f"  {status} {wt['branch']}")
                    formatter.text(f"     {wt['path']}")
            else:
                formatter.text("No active worktrees found")

            if archived:
                formatter.text(f"\nArchived worktrees ({len(archived)}):")
                for wt in archived:
                    status = "✓" if wt["exists"] else "✗"
                    formatter.text(f"  {status} {Path(wt['path']).name}")
                    formatter.text(f"     {wt['path']}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_list_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
