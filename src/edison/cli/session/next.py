"""
Edison session next command.

SUMMARY: Compute recommended next actions for a session

Session ID is optional - auto-resolved from environment/worktree/process.
Most users should NOT pass --session unless resuming a different session.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.session import next as session_next

SUMMARY = "Compute recommended next actions for a session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",  # Optional - auto-resolved if not provided (task 001-session-id-inference)
        default=None,
        help=(
            "Session identifier (optional; auto-resolved from AGENTS_SESSION, "
            "worktree .session-id, or process tree). Only pass this to resume "
            "a different/older session."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum actions to return (0 = use default from manifest)",
    )
    parser.add_argument(
        "--scope",
        choices=["tasks", "qa", "session"],
        help="Restrict planning to a specific domain",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compute next actions - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Resolve session ID using canonical detection (task 001-session-id-inference)
        session_id = args.session_id
        if not session_id:
            from edison.core.session.core.id import require_session_id

            repo_root = get_repo_root(args)
            session_id = require_session_id(project_root=repo_root)

        # Build argv for the core library's main()
        fwd_argv = [
            "session-next",
            session_id,
        ]
        if args.limit:
            fwd_argv.extend(["--limit", str(args.limit)])
        if args.scope:
            fwd_argv.extend(["--scope", args.scope])
        if getattr(args, "json", False):
            fwd_argv.append("--json")
        if getattr(args, "repo_root", None):
            fwd_argv.extend(["--repo-root", str(args.repo_root)])

        # Swap argv and call core library main
        original_argv = sys.argv
        try:
            sys.argv = fwd_argv
            session_next.main()
        finally:
            sys.argv = original_argv

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
