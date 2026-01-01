"""
Edison session cleanup_stale command.

SUMMARY: Clean up stale sessions (restores records to global queues)
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Clean up stale sessions (restores records to global queues)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which sessions would be cleaned (no changes)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Clean up stale sessions - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)

        if getattr(args, "dry_run", False):
            # Dry-run: report stale sessions without mutating state
            from edison.core.session.lifecycle.recovery import is_session_expired
            from edison.core.session.persistence.repository import SessionRepository
            from edison.core.session._config import get_config

            repo = SessionRepository(project_root=project_root)
            config = get_config(project_root)
            active_state = config.get_initial_session_state()
            active_sessions = [s.id for s in repo.list_by_state(active_state)]
            stale = [
                sid for sid in active_sessions
                if is_session_expired(sid, project_root=project_root)
            ]

            payload = {"stale": stale, "count": len(stale), "dry_run": True}
            if formatter.json_mode:
                formatter.json_output(payload)
            else:
                if stale:
                    formatter.text("Stale sessions (dry-run, would be cleaned):")
                    for sid in stale:
                        formatter.text(f"  - {sid}")
                    formatter.text("")
                    formatter.text(f"Total: {len(stale)} stale session(s)")
                    formatter.text("")
                    formatter.text("Run without --dry-run to clean them up.")
                else:
                    formatter.text("No stale sessions detected.")
            return 0

        # Actual cleanup - use the existing core function
        from edison.core.session.lifecycle.recovery import cleanup_expired_sessions

        cleaned = cleanup_expired_sessions()

        payload = {"cleaned": cleaned, "count": len(cleaned)}
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            if cleaned:
                formatter.text("Cleaned up stale sessions:")
                for sid in cleaned:
                    formatter.text(f"  - {sid}")
                formatter.text("")
                formatter.text(f"Total: {len(cleaned)} session(s) cleaned")
                formatter.text("Records have been restored to global queues.")
            else:
                formatter.text("No stale sessions to clean up.")

        return 0

    except Exception as e:
        formatter.error(e, error_code="cleanup_stale_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
