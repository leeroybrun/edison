"""
Edison git worktree-health command.

SUMMARY: Check worktree health
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    """Check worktree health - delegates to worktree library."""
    from edison.core.session import worktree

    try:
        if args.session_id:
            # Check specific session worktree
            worktree_path, branch_name = worktree.resolve_worktree_target(args.session_id)

            # Check if worktree is registered
            is_registered = worktree.is_registered_worktree(worktree_path)

            # Check if path exists and is healthy
            from edison.core.session.worktree import _git_is_healthy
            is_healthy = _git_is_healthy(worktree_path) if worktree_path.exists() else False

            result = {
                "session_id": args.session_id,
                "path": str(worktree_path),
                "branch": branch_name,
                "exists": worktree_path.exists(),
                "registered": is_registered,
                "healthy": is_healthy,
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Worktree health for session: {args.session_id}")
                print(f"  Path: {worktree_path}")
                print(f"  Branch: {branch_name}")
                print(f"  Exists: {'✓' if worktree_path.exists() else '✗'}")
                print(f"  Registered: {'✓' if is_registered else '✗'}")
                print(f"  Healthy: {'✓' if is_healthy else '✗'}")

            return 0 if is_healthy else 1

        else:
            # Check global worktree health
            is_healthy, notes = worktree.worktree_health_check()

            result = {
                "healthy": is_healthy,
                "notes": notes,
            }

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Worktree system health: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")
                if notes:
                    print("\nDetails:")
                    for note in notes:
                        print(f"  {note}")

            return 0 if is_healthy else 1

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
