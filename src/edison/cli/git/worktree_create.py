"""
Edison git worktree-create command.

SUMMARY: Create git worktree for session
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Create git worktree for session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        type=str,
        help="Session ID to create worktree for",
    )
    parser.add_argument(
        "--branch",
        type=str,
        help="Base branch to branch from (default: main)",
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Override worktree path",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies after creation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating it",
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
    """Create git worktree - delegates to worktree library."""
    from edison.core.session import worktree

    try:
        worktree_path, branch_name = worktree.create_worktree(
            session_id=args.session_id,
            base_branch=args.branch,
            install_deps=args.install_deps if args.install_deps else None,
            dry_run=args.dry_run,
        )

        result = {
            "session_id": args.session_id,
            "worktree_path": str(worktree_path) if worktree_path else None,
            "branch_name": branch_name,
            "dry_run": args.dry_run,
        }

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if args.dry_run:
                print(f"Would create worktree:")
                print(f"  Path: {worktree_path}")
                print(f"  Branch: {branch_name}")
            else:
                print(f"Created worktree for session: {args.session_id}")
                print(f"  Path: {worktree_path}")
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
