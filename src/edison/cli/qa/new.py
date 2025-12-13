"""
Edison qa new command.

SUMMARY: Create new QA brief for a task
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa.evidence import EvidenceService

SUMMARY = "Create new QA brief for a task"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--owner",
        type=str,
        default="_unassigned_",
        help="Validator owner (default: _unassigned_)",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: create new round)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Create QA brief - uses EvidenceService.create_qa_brief()."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        # Use EvidenceService for QA brief creation
        ev_svc = EvidenceService(args.task_id, project_root=repo_root)

        # Create QA brief using the canonical method
        qa_brief = ev_svc.create_qa_brief(
            session_id=args.session,
            round_num=args.round,
        )

        # Get the round number and path
        round_num = ev_svc.get_current_round() or 1
        round_dir = ev_svc.ensure_round(round_num)
        brief_path = round_dir / "qa-brief.json"

        result = {
            "qaPath": str(brief_path),
            "round": round_num,
            "owner": args.owner,
            "brief": qa_brief,
        }

        formatter.json_output(result) if formatter.json_mode else formatter.text(
            f"Created QA brief for {args.task_id} round {round_num}\n  Path: {brief_path}"
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="qa_new_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
