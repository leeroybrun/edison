"""
Edison git worktree-cleanup command.

SUMMARY: Clean up session worktree
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_force_flag

SUMMARY = "Clean up session worktree"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to cleanup worktree for",
    )
    add_force_flag(parser)
    parser.add_argument(
        "--delete-branch",
        action="store_true",
        help="Also delete the session branch",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Cleanup git worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import worktree

    try:
        # Resolve the worktree path and branch name for this session
        worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

        if not worktree_path.exists():
            if args.json:
                formatter.json_output({"error": "Worktree not found", "path": str(worktree_path)})
            else:
                formatter.error(f"Worktree not found: {worktree_path}", error_code="worktree_not_found")
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
            formatter.json_output(result)
        else:
            formatter.text(f"Cleaned up worktree for session: {args.session_id}")
            formatter.text(f"  Path: {worktree_path}")
            if args.delete_branch:
                formatter.text(f"  Deleted branch: {branch_name}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_cleanup_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
