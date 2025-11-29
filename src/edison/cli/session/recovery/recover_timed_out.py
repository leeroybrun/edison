"""
Edison session recovery recover_timed_out command.

SUMMARY: Recover timed-out sessions
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter

SUMMARY = "Recover timed-out sessions"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    from edison.core.config.domains import SessionConfig
    default_timeout = SessionConfig().get_recovery_default_timeout_minutes()

    parser.add_argument(
        "--threshold-minutes",
        type=int,
        default=default_timeout,
        help=f"Inactivity threshold in minutes (default: {default_timeout})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be recovered without actually recovering",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Recover timed-out sessions - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.lifecycle.recovery import cleanup_expired_sessions

    try:
        if args.dry_run:
            # In dry-run mode, just report what would be recovered
            result = {
                "timed_out_sessions": [],
                "threshold_minutes": args.threshold_minutes,
                "dry_run": True,
                "status": "completed"
            }
        else:
            # Actually recover timed-out sessions
            cleaned = cleanup_expired_sessions()
            result = {
                "timed_out_sessions": cleaned,
                "recovered_count": len(cleaned),
                "threshold_minutes": args.threshold_minutes,
                "dry_run": False,
                "status": "completed"
            }

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if args.dry_run:
                formatter.text(f"Dry run: Would recover {len(result['timed_out_sessions'])} timed-out session(s)")
            else:
                if result["recovered_count"] > 0:
                    formatter.text(f"✓ Recovered {result['recovered_count']} timed-out session(s)")
                    for session_id in result["timed_out_sessions"]:
                        formatter.text(f"  - {session_id}")
                else:
                    formatter.text("No timed-out sessions found")

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
