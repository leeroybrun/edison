"""
Edison git worktree-health command.

SUMMARY: Check worktree health
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag

SUMMARY = "Check worktree health"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        type=str,
        help="Session ID to check (optional - checks all if not provided)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix unhealthy worktrees",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Check worktree health - delegates to worktree library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session import worktree

    try:
        if args.session_id:
            # Check specific session worktree
            worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

            # Check if worktree is registered
            is_registered = worktree.is_worktree_registered(worktree_path)

            # Check if path exists and is healthy
            from edison.core.utils.git.worktree import check_worktree_health
            is_healthy = check_worktree_health(worktree_path) if worktree_path.exists() else False

            result = {
                "session_id": args.session_id,
                "path": str(worktree_path),
                "branch": branch_name,
                "exists": worktree_path.exists(),
                "registered": is_registered,
                "healthy": is_healthy,
            }

            if args.json:
                formatter.json_output(result)
            else:
                formatter.text(f"Worktree health for session: {args.session_id}")
                formatter.text(f"  Path: {worktree_path}")
                formatter.text(f"  Branch: {branch_name}")
                formatter.text(f"  Exists: {'✓' if worktree_path.exists() else '✗'}")
                formatter.text(f"  Registered: {'✓' if is_registered else '✗'}")
                formatter.text(f"  Healthy: {'✓' if is_healthy else '✗'}")

            return 0 if is_healthy else 1

        else:
            # Check global worktree health
            is_healthy, notes = worktree.worktree_health_check()

            result = {
                "healthy": is_healthy,
                "notes": notes,
            }

            if args.json:
                formatter.json_output(result)
            else:
                formatter.text(f"Worktree system health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
                if notes:
                    formatter.text("\nDetails:")
                    for note in notes:
                        formatter.text(f"  {note}")

            return 0 if is_healthy else 1

    except Exception as e:
        formatter.error(e, error_code="worktree_health_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
