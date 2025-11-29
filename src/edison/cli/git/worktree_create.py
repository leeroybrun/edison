"""
Edison git worktree-create command.

SUMMARY: Create git worktree for session
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_dry_run_flag

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
    add_dry_run_flag(parser)
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create git worktree - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

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
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Would create worktree:")
                formatter.text(f"  Path: {worktree_path}")
                formatter.text(f"  Branch: {branch_name}")
            else:
                formatter.text(f"Created worktree for session: {args.session_id}")
                formatter.text(f"  Path: {worktree_path}")
                formatter.text(f"  Branch: {branch_name}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="worktree_create_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
