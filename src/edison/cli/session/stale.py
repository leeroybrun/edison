"""
Edison session stale command.

SUMMARY: List stale sessions (inactive beyond timeout, but resumable)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List stale sessions (inactive beyond timeout)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list",
        help="List all stale sessions (non-destructive, read-only)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _get_stale_sessions(project_root: Path) -> List[Dict[str, Any]]:
    """Get list of stale sessions with their metadata.

    A session is considered stale if it has exceeded the inactivity timeout
    (configured via session.recovery.timeoutHours), but it remains resumable.

    Args:
        project_root: Project root path

    Returns:
        List of stale session dictionaries with id, state, lastActive, inactiveHours
    """
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session.lifecycle.recovery import is_session_expired
    from edison.core.session._config import get_config

    repo = SessionRepository(project_root=project_root)
    config = get_config(project_root)

    # Get the initial/active state from config
    active_state = config.get_initial_session_state()
    active_sessions = repo.list_by_state(active_state)

    stale_sessions: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for session in active_sessions:
        if is_session_expired(session.id, project_root=project_root):
            # Calculate inactivity duration
            # updated_at maps to lastActive in session JSON
            last_active = session.metadata.updated_at
            inactive_hours = 0.0
            last_active_str = ""

            if last_active:
                if isinstance(last_active, datetime):
                    last_dt = last_active
                else:
                    # Parse ISO timestamp
                    from edison.core.utils.time import parse_iso8601

                    last_dt = parse_iso8601(str(last_active), repo_root=project_root)

                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)

                delta = now - last_dt
                inactive_hours = round(delta.total_seconds() / 3600, 1)
                last_active_str = last_dt.isoformat()

            stale_sessions.append({
                "id": session.id,
                "state": session.state,
                "lastActive": last_active_str,
                "inactiveHours": inactive_hours,
            })

    return stale_sessions


def main(args: argparse.Namespace) -> int:
    """List stale sessions - non-destructive, read-only operation."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        if not getattr(args, "list", False):
            # No action specified, show usage hint
            if formatter.json_mode:
                formatter.json_output({
                    "error": "No action specified",
                    "hint": "Use --list to show stale sessions",
                })
            else:
                formatter.text("Usage: edison session stale --list")
                formatter.text("")
                formatter.text("Options:")
                formatter.text("  --list    List all stale sessions (non-destructive)")
                formatter.text("")
                formatter.text("Stale sessions are inactive beyond the timeout threshold,")
                formatter.text("but remain resumable. Use 'edison session resume <id>'")
                formatter.text("to continue work, or 'edison session cleanup-stale'")
                formatter.text("to clean them up.")
            return 1

        project_root = get_repo_root(args)
        stale_sessions = _get_stale_sessions(project_root)

        if formatter.json_mode:
            formatter.json_output({
                "stale_sessions": stale_sessions,
                "count": len(stale_sessions),
            })
        else:
            if stale_sessions:
                formatter.text("Stale sessions (inactive beyond timeout, but resumable):")
                formatter.text("")
                for sess in stale_sessions:
                    formatter.text(f"  - {sess['id']}")
                    formatter.text(f"    State: {sess['state']}")
                    formatter.text(f"    Inactive: {sess['inactiveHours']} hours")
                    if sess["lastActive"]:
                        formatter.text(f"    Last active: {sess['lastActive']}")
                    formatter.text("")
                formatter.text(f"Total: {len(stale_sessions)} stale session(s)")
                formatter.text("")
                formatter.text("To resume: edison session resume <session-id>")
                formatter.text("To cleanup: edison session cleanup-stale")
            else:
                formatter.text("No stale sessions found.")

        return 0

    except Exception as e:
        formatter.error(e, error_code="stale_list_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
