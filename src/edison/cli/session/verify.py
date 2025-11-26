"""
Edison session verify command.

SUMMARY: Verify a session against closing-phase guards
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

SUMMARY = "Verify a session against closing-phase guards"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=["closing"],
        help="Lifecycle phase to verify (currently only 'closing' supported)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for automation",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Verify session health - delegates to core library."""
    from edison.core.session import store as session_store
    from edison.core.session.verify import verify_session_health

    try:
        session_id = session_store.validate_session_id(args.session_id)
        health = verify_session_health(session_id)

        if args.json:
            print(json.dumps(health, indent=2, default=str))
        else:
            if health.get("ok"):
                print(f"Session {session_id} passed {args.phase} verification.")
            else:
                print(f"Session {session_id} failed {args.phase} verification:")
                for detail in health.get("details", []):
                    print(f"  - {detail}")

                # Print category summaries
                categories = health.get("categories", {})
                if categories.get("stateMismatches"):
                    print(f"\nState mismatches: {len(categories['stateMismatches'])}")
                if categories.get("unexpectedStates"):
                    print(f"Unexpected states: {len(categories['unexpectedStates'])}")
                if categories.get("missingQA"):
                    print(f"Missing QA: {len(categories['missingQA'])}")
                if categories.get("missingEvidence"):
                    print(f"Missing evidence: {len(categories['missingEvidence'])}")
                if categories.get("bundleNotApproved"):
                    print(f"Bundle not approved: {len(categories['bundleNotApproved'])}")

        return 0 if health.get("ok") else 1

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
