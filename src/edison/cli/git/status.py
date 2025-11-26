"""
Edison git status command.

SUMMARY: Show Edison-aware git status
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Show Edison-aware git status"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session",
        type=str,
        help="Filter to files in session worktree",
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Filter to files related to a task",
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
    """Show git status - delegates to git library."""
    from edison.core.git import status as git_status
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()

        # Get git status
        result = git_status.get_status(
            repo_root=repo_root,
            session_id=args.session,
            task_id=args.task,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Branch: {result.get('branch', 'unknown')}")
            print(f"Clean: {result.get('clean', False)}")
            if result.get("staged"):
                print(f"\nStaged ({len(result['staged'])} files):")
                for f in result["staged"][:10]:
                    print(f"  + {f}")
                if len(result["staged"]) > 10:
                    print(f"  ... and {len(result['staged']) - 10} more")
            if result.get("modified"):
                print(f"\nModified ({len(result['modified'])} files):")
                for f in result["modified"][:10]:
                    print(f"  M {f}")
                if len(result["modified"]) > 10:
                    print(f"  ... and {len(result['modified']) - 10} more")
            if result.get("untracked"):
                print(f"\nUntracked ({len(result['untracked'])} files):")
                for f in result["untracked"][:10]:
                    print(f"  ? {f}")
                if len(result["untracked"]) > 10:
                    print(f"  ... and {len(result['untracked']) - 10} more")

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
