"""
Edison session create command.

SUMMARY: Create a new Edison session
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.session import lifecycle as session_manager
from edison.core.session.core.id import validate_session_id
from edison.core.exceptions import SessionError
from edison.core.session.lifecycle.autostart import SessionAutoStart
from pathlib import Path

SUMMARY = "Create a new Edison session"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session-id",
        "--id",
        dest="session_id",
        required=True,
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--owner",
        default="system",
        help="Session owner (default: system)",
    )
    parser.add_argument(
        "--mode",
        default="start",
        help="Session mode (default: start)",
    )
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="Skip worktree creation",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies in worktree (if creating worktree)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create a new session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        session_id = validate_session_id(args.session_id)

        # Determine worktree creation
        create_wt = not args.no_worktree
        install_deps = args.install_deps if args.install_deps else None

        # Create the session
        sess_path = session_manager.create_session(
            session_id=session_id,
            owner=args.owner,
            mode=args.mode,
            install_deps=install_deps,
            create_wt=create_wt,
        )

        # Load session data for output
        session = session_manager.get_session(session_id)

        # Trigger autostart if mode is "start"
        if args.mode == "start":
            try:

                repo_root = get_repo_root(args)
                autostart = SessionAutoStart(project_root=repo_root)
                autostart_result = autostart.start(process=session_id, orchestrator_profile=None)
                # Autostart launched in background, don't wait
            except Exception:
                # Autostart is optional; if it fails, session is still created
                pass

        if formatter.json_mode:
            output = {
                "status": "created",
                "session_id": session_id,
                "path": str(sess_path),
                "session": session,
            }
            formatter.json_output(output)
        else:
            formatter.text(f"✓ Created session: {session_id}")
            formatter.text(f"  Path: {sess_path}")
            formatter.text(f"  Owner: {args.owner}")
            formatter.text(f"  Mode: {args.mode}")
            if session.get("git", {}).get("worktreePath"):
                formatter.text(f"  Worktree: {session['git']['worktreePath']}")
            if session.get("git", {}).get("branchName"):
                formatter.text(f"  Branch: {session['git']['branchName']}")

        return 0

    except SessionError as e:
        formatter.error(e, error_code="session_error")
        return 1

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
