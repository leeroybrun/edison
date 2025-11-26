"""
Edison session create command.

SUMMARY: Create a new Edison session
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

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
    """Create a new session - delegates to core library."""
    from edison.core.session import manager as session_manager
    from edison.core.session import store as session_store
    from edison.core.exceptions import SessionError

    try:
        session_id = session_store.validate_session_id(args.session_id)

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
                from edison.core.session.autostart import SessionAutoStart
                from edison.core.utils.paths import resolve_project_root
                from pathlib import Path

                repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
                autostart = SessionAutoStart(project_root=repo_root)
                autostart_result = autostart.start(process=session_id, orchestrator_profile=None)
                # Autostart launched in background, don't wait
            except Exception:
                # Autostart is optional; if it fails, session is still created
                pass

        if args.json:
            output = {
                "status": "created",
                "session_id": session_id,
                "path": str(sess_path),
                "session": session,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            print(f"✓ Created session: {session_id}")
            print(f"  Path: {sess_path}")
            print(f"  Owner: {args.owner}")
            print(f"  Mode: {args.mode}")
            if session.get("git", {}).get("worktreePath"):
                print(f"  Worktree: {session['git']['worktreePath']}")
            if session.get("git", {}).get("branchName"):
                print(f"  Branch: {session['git']['branchName']}")

        return 0

    except SessionError as e:
        if args.json:
            print(json.dumps({"error": "session_error", "message": str(e)}, indent=2))
        else:
            print(f"Error: {e}")
        return 1

    except Exception as e:
        if args.json:
            print(json.dumps({"error": "unexpected_error", "message": str(e)}, indent=2))
        else:
            print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
