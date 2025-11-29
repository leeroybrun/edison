"""
Edison qa bundle command.

SUMMARY: Create or inspect QA validation bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.qa import bundler
from edison.core.qa.evidence import EvidenceService

SUMMARY = "Create or inspect QA validation bundle"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: latest round)",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create new bundle summary",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect existing bundle",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mark bundle as approved",
    )
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Mark bundle as rejected",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Bundle management - delegates to QA library."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        # Determine round number using EvidenceService
        round_num = args.round
        if round_num is None:
            svc = EvidenceService(args.task_id, project_root=repo_root)
            round_num = svc.get_current_round()
            if round_num is None:
                formatter.error("No rounds found for task", error_code="no_rounds")
                return 1

        # Load or create bundle
        if args.create:
            summary = {
                "task_id": args.task_id,
                "round": round_num,
                "status": "pending",
                "validators": {},
            }
            path = bundler.write_bundle_summary(args.task_id, round_num, summary)
            formatter.json_output({"created": str(path), "summary": summary}) if formatter.json_mode else formatter.text(f"Created bundle: {path}")
        elif args.approve or args.reject:
            summary = bundler.load_bundle_summary(args.task_id, round_num)
            if not summary:
                formatter.error("Bundle not found", error_code="bundle_not_found")
                return 1
            summary["status"] = "approved" if args.approve else "rejected"
            path = bundler.write_bundle_summary(args.task_id, round_num, summary)
            formatter.json_output({"updated": str(path), "summary": summary}) if formatter.json_mode else formatter.text(f"Updated bundle status to: {summary['status']}")
        else:
            # Default: inspect
            summary = bundler.load_bundle_summary(args.task_id, round_num)
            if formatter.json_mode:
                formatter.json_output(summary if summary else {"error": "Bundle not found"})
            else:
                if summary:
                    formatter.text(f"Bundle for {args.task_id} round {round_num}:")
                    formatter.text(f"  Status: {summary.get('status', 'unknown')}")
                    formatter.text(f"  Validators: {len(summary.get('validators', {}))}")
                else:
                    formatter.text(f"No bundle found for {args.task_id} round {round_num}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="bundle_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
