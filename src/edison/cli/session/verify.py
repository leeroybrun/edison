"""
Edison session verify command.

SUMMARY: Verify a session against closing-phase guards
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, OutputFormatter
from edison.core.session import validate_session_id
from edison.core.session.lifecycle.verify import verify_session_health

SUMMARY = "Verify a session against closing-phase guards"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--phase",
        choices=["closing"],
        default="closing",
        help="Verification phase (currently only 'closing' is supported)",
    )
    add_json_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Verify session health - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        session_id = validate_session_id(args.session_id)

        health = verify_session_health(session_id)

        if formatter.json_mode:
            formatter.json_output(health)
        else:
            if health.get("ok"):
                formatter.text(f"Session {session_id} passed {args.phase} verification.")
            else:
                formatter.text(f"Session {session_id} failed {args.phase} verification:")
                for detail in health.get("details", []):
                    formatter.text(f"  - {detail}")

                # Print category summaries
                categories = health.get("categories", {})
                if categories.get("stateMismatches"):
                    formatter.text(f"\nState mismatches: {len(categories['stateMismatches'])}")
                if categories.get("unexpectedStates"):
                    formatter.text(f"Unexpected states: {len(categories['unexpectedStates'])}")
                if categories.get("missingQA"):
                    formatter.text(f"Missing QA: {len(categories['missingQA'])}")
                if categories.get("missingEvidence"):
                    formatter.text(f"Missing evidence: {len(categories['missingEvidence'])}")
                if categories.get("bundleNotApproved"):
                    formatter.text(f"Bundle not approved: {len(categories['bundleNotApproved'])}")

        return 0 if health.get("ok") else 1

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
