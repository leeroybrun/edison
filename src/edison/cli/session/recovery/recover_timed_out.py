"""
Edison session recovery recover_timed_out command.

SUMMARY: Recover timed-out sessions
"""
from __future__ import annotations

import argparse
import json
import sys

SUMMARY = "Recover timed-out sessions"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--threshold-minutes",
        type=int,
        default=60,
        help="Inactivity threshold in minutes (default: 60)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be recovered without actually recovering",
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
    """Recover timed-out sessions - delegates to core library."""
    from edison.core.session.recovery import cleanup_expired_sessions

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

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if args.dry_run:
                print(f"Dry run: Would recover {len(result['timed_out_sessions'])} timed-out session(s)")
            else:
                if result["recovered_count"] > 0:
                    print(f"✓ Recovered {result['recovered_count']} timed-out session(s)")
                    for session_id in result["timed_out_sessions"]:
                        print(f"  - {session_id}")
                else:
                    print("No timed-out sessions found")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
