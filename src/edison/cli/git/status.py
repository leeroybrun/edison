"""
Edison git status command.

SUMMARY: Show Edison-aware git status
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag

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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Show git status - delegates to git library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.git import status as git_status
    
    try:
        repo_root = get_repo_root(args)

        # Get git status
        result = git_status.get_status(
            repo_root=repo_root,
            session_id=args.session,
            task_id=args.task,
        )

        if args.json:
            formatter.json_output(result)
        else:
            formatter.text(f"Branch: {result.get('branch', 'unknown')}")
            formatter.text(f"Clean: {result.get('clean', False)}")
            if result.get("staged"):
                formatter.text(f"\nStaged ({len(result['staged'])} files):")
                for f in result["staged"][:10]:
                    formatter.text(f"  + {f}")
                if len(result["staged"]) > 10:
                    formatter.text(f"  ... and {len(result['staged']) - 10} more")
            if result.get("modified"):
                formatter.text(f"\nModified ({len(result['modified'])} files):")
                for f in result["modified"][:10]:
                    formatter.text(f"  M {f}")
                if len(result["modified"]) > 10:
                    formatter.text(f"  ... and {len(result['modified']) - 10} more")
            if result.get("untracked"):
                formatter.text(f"\nUntracked ({len(result['untracked'])} files):")
                for f in result["untracked"][:10]:
                    formatter.text(f"  ? {f}")
                if len(result["untracked"]) > 10:
                    formatter.text(f"  ... and {len(result['untracked']) - 10} more")

        return 0

    except Exception as e:
        formatter.error(e, error_code="git_status_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
