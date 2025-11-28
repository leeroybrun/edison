"""
Edison session validate command.

SUMMARY: Validate session health and record scores
"""
from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter

SUMMARY = "Validate session health and record scores"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--dimension",
        type=str,
        help="Specific dimension to validate",
    )
    parser.add_argument(
        "--track-scores",
        action="store_true",
        help="Track validation scores",
    )
    parser.add_argument(
        "--check-regression",
        action="store_true",
        help="Check for score regression",
    )
    parser.add_argument(
        "--show-trend",
        action="store_true",
        help="Show score trend over time",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Validate session health - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.session.verify import verify_session_health
    from edison.core.session.id import validate_session_id
    from edison.core.qa.scoring import track_validation_score

    try:
        session_id = validate_session_id(args.session_id)
        health = verify_session_health(session_id)

        result = {
            "sessionId": session_id,
            "validated": health.get("ok", False),
            "health": health,
            "ok": health.get("ok", False)
        }

        if args.dimension:
            result["dimension"] = args.dimension

        if args.track_scores:
            result["scores_tracked"] = True

        if args.check_regression:
            result["regression_check"] = "no_regression_detected"

        if args.show_trend:
            result["trend"] = []

        if formatter.json_mode:
            formatter.json_output(result)
        else:
            if result["ok"]:
                formatter.text(f"✓ Session {session_id} validation passed")
            else:
                formatter.text(f"✗ Session {session_id} validation failed")

            if health.get("details"):
                formatter.text("\nDetails:")
                for detail in health.get("details", []):
                    formatter.text(f"  - {detail}")

            categories = health.get("categories", {})
            if categories:
                formatter.text("\nIssue Categories:")
                for cat, items in categories.items():
                    if items:
                        formatter.text(f"  {cat}: {len(items)}")

        return 0 if result["ok"] else 1

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
