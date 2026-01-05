"""
Edison task done command.

SUMMARY: Complete a task (wip→done) with guard enforcement.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_session_id,
)
from edison.cli._utils import resolve_existing_task_id
from edison.core.task import TaskQAWorkflow

SUMMARY = "Complete a task (wip→done) with guard enforcement"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task ID to complete (supports unique prefix shorthand like '12007')",
    )
    parser.add_argument(
        "--session",
        help="Session completing the task (required; enforces session-scoped safety)",
    )
    parser.add_argument(
        "--skip-context7",
        action="store_true",
        help="Bypass Context7 checks for verified false positives only (requires --skip-context7-reason).",
    )
    parser.add_argument(
        "--skip-context7-reason",
        help="Justification for Context7 bypass (required when --skip-context7 is set).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        session_id = resolve_session_id(project_root=project_root, explicit=args.session, required=True)

        resolved = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.record_id))
        if str(resolved) != str(args.record_id):
            print(
                f"Resolved task id {args.record_id!r} -> {resolved!r}",
                file=sys.stderr,
            )

        skip_context7 = bool(getattr(args, "skip_context7", False))
        skip_context7_reason = str(getattr(args, "skip_context7_reason", "") or "").strip()
        if skip_context7 and not skip_context7_reason:
            raise ValueError("--skip-context7 requires --skip-context7-reason")
        if (not skip_context7) and skip_context7_reason:
            raise ValueError("--skip-context7-reason requires --skip-context7")

        if skip_context7:
            print(
                f"WARNING: bypassing Context7 checks for task {resolved} ({skip_context7_reason})",
                file=sys.stderr,
            )

        workflow = TaskQAWorkflow(project_root=project_root)
        task_entity = workflow.complete_task(
            resolved,
            session_id,
            enforce_tdd=True,
            skip_context7=skip_context7,
            skip_context7_reason=skip_context7_reason,
        )

        payload = {
            "record_id": resolved,
            "done": True,
            "state": task_entity.state,
            "session_id": session_id,
        }
        if skip_context7:
            payload["skip_context7"] = True
            payload["skip_context7_reason"] = skip_context7_reason
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text(f"Task {resolved} marked as done (moved to {task_entity.state}).")
        return 0

    except Exception as e:
        formatter.error(e, error_code="done_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
