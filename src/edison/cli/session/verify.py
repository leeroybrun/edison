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
        try:
            from edison.core.workflow.checklists.session_close_preflight import (
                SessionClosePreflightChecklistEngine,
            )

            close_checklist = SessionClosePreflightChecklistEngine().compute(session_id=session_id)
        except Exception:
            close_checklist = None

        if formatter.json_mode:
            if isinstance(close_checklist, dict):
                formatter.json_output({**health, "closeChecklist": close_checklist})
            else:
                formatter.json_output(health)
        else:
            if health.get("ok"):
                formatter.text(f"Session {session_id} passed {args.phase} verification.")
            else:
                formatter.text(f"Session {session_id} failed {args.phase} verification:")
                if isinstance(close_checklist, dict):
                    _display_checklist(formatter=formatter, checklist=close_checklist)
                else:
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
                if categories.get("bundleWrongPreset"):
                    formatter.text(f"Bundle wrong preset: {len(categories['bundleWrongPreset'])}")

        return 0 if health.get("ok") else 1

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


def _display_checklist(*, formatter: OutputFormatter, checklist: dict[str, object]) -> None:
    items = checklist.get("items") if isinstance(checklist, dict) else None
    if not isinstance(items, list) or not items:
        return

    has_blockers = bool(checklist.get("hasBlockers", False))
    header = "Session close preflight checklist:"
    if has_blockers:
        header += " (BLOCKERS present)"
    formatter.text(header)

    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Unknown")
        severity = str(item.get("severity") or "info")
        status = str(item.get("status") or "unknown")
        tag = "OK"
        if status != "ok":
            tag = "BLOCK" if severity == "blocker" else ("WARN" if severity == "warning" else "INFO")
        formatter.text(f"  - [{tag}] {title}")
        rationale = str(item.get("rationale") or "").strip()
        if rationale and status != "ok":
            formatter.text(f"      {rationale}")
        cmds = item.get("suggestedCommands") or []
        if status != "ok" and isinstance(cmds, list) and cmds:
            for cmd in cmds[:3]:
                formatter.text(f"      -> {cmd}")

    formatter.text("")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
