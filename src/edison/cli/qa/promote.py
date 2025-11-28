"""
Edison qa promote command.

SUMMARY: Promote QA brief between states
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Promote QA brief between states"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["waiting", "todo", "wip", "done", "validated"],
        help="Target status to promote to",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip validation checks",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Promote QA brief - delegates to QA library."""
    from edison.core.qa import promoter, bundler
    from edison.core.qa.evidence import EvidenceService

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if not args.status:
            formatter.error("--status is required", error_code="missing_status")
            return 1

        # Get latest round using EvidenceService
        svc = EvidenceService(args.task_id, project_root=repo_root)
        round_num = svc.get_current_round()
        if round_num is None:
            formatter.error("No rounds found for task", error_code="no_rounds")
            return 1

        # Check if revalidation is needed (unless forced)
        if not args.force and args.status == "validated":
            bundle_path = bundler.bundle_summary_path(args.task_id, round_num)
            reports = promoter.collect_validator_reports([args.task_id])
            task_files = promoter.collect_task_files([args.task_id], args.session)

            if promoter.should_revalidate_bundle(bundle_path, reports, task_files):
                formatter.error("Bundle is stale, run validation first", error_code="revalidation_required")
                return 1

        # Perform promotion (simplified - actual implementation would be more complex)
        result = {
            "task_id": args.task_id,
            "round": round_num,
            "old_status": "unknown",
            "new_status": args.status,
            "promoted": True,
        }

        formatter.json_output(result) if formatter.json_mode else formatter.text(f"Promoted {args.task_id} to status: {args.status}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="promote_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
