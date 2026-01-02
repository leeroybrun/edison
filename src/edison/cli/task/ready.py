"""
Edison task ready command.

SUMMARY: List tasks ready to be claimed or mark task as ready (complete)
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
from pathlib import Path

from edison.core.task import TaskQAWorkflow, normalize_record_id

SUMMARY = "List tasks ready to be claimed or mark task as ready (complete)"


def _record_context7_bypass(task_id: str, project_root: Path) -> None:
    """Record Context7 bypass in the implementation report for audit trail.

    Appends a bypass notice to the implementation report YAML frontmatter
    and body to ensure the bypass is auditable.
    """
    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.time import utc_timestamp

    try:
        ev_svc = EvidenceService(task_id, project_root=project_root)
        current_round = ev_svc.get_current_round()
        if current_round is None:
            return

        round_dir = ev_svc.get_round_dir(current_round)
        impl_report_path = round_dir / ev_svc.implementation_filename

        if not impl_report_path.exists():
            return

        content = impl_report_path.read_text(encoding="utf-8")

        # Add bypass notice to the report
        bypass_notice = f"\n\n## Context7 Bypass Notice\n\n**WARNING**: Context7 evidence checks were bypassed at {utc_timestamp()}.\n\nThis task was marked as ready without complete Context7 evidence markers.\nReview Context7 configuration: `edison config show context7 --format yaml`\n"

        # Append the bypass notice to the end of the file
        updated_content = content.rstrip() + bypass_notice
        impl_report_path.write_text(updated_content, encoding="utf-8")
    except Exception:
        # Best-effort audit trail - don't fail the command
        pass


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        nargs="?",
        help="Task ID to mark as ready/complete (if omitted, lists all ready tasks)",
    )
    parser.add_argument(
        "--session",
        help="Filter by session",
    )
    parser.add_argument(
        "--skip-context7",
        action="store_true",
        default=False,
        dest="skip_context7",
        help="Bypass Context7 evidence checks (use with caution - leaves audit trace)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        default=False,
        dest="run_deprecated",
        help="DEPRECATED: Use 'edison evidence capture' instead",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List ready tasks or mark task as ready - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    # Check for deprecated --run flag
    if getattr(args, "run_deprecated", False):
        deprecation_message = (
            "The '--run' flag has been removed.\n\n"
            "Evidence must come from real command runners, not placeholders.\n"
            "Use the following commands instead:\n\n"
            "  edison evidence init <task-id>      Initialize evidence round directory\n"
            "  edison evidence capture <task-id>   Run CI commands and capture output as evidence\n"
            "  edison evidence status <task-id>    Check evidence status for a task\n\n"
            "Example workflow:\n"
            "  1. edison evidence init my-task\n"
            "  2. edison evidence capture my-task\n"
            "  3. edison task ready my-task"
        )
        if formatter.json_mode:
            formatter.json_output({
                "error": "run_flag_deprecated",
                "message": deprecation_message,
            })
        else:
            formatter.error(RuntimeError(deprecation_message), error_code="run_flag_deprecated")
        return 1

    try:
        # Resolve project root
        project_root = get_repo_root(args)
        skip_context7 = getattr(args, "skip_context7", False)

        if args.record_id:
            # Ready/complete a specific task (move from wip -> done)
            record_id = normalize_record_id("task", args.record_id)

            session_id = resolve_session_id(
                project_root=project_root,
                explicit=args.session,
                required=True,
            )
            assert session_id is not None, "resolve_session_id with required=True should not return None"

            # Print warning if bypassing Context7
            context7_bypassed = False
            if skip_context7:
                import sys
                warning_msg = (
                    "[WARNING] Context7 evidence checks are being BYPASSED.\n"
                    "This bypass will be recorded in the implementation report.\n"
                    "Use 'edison config show context7 --format yaml' to view configuration."
                )
                print(warning_msg, file=sys.stderr)
                context7_bypassed = True

            # Use TaskQAWorkflow.complete_task() to move from wip -> done
            workflow = TaskQAWorkflow(project_root=project_root)
            task_entity = workflow.complete_task(
                record_id,
                session_id,
                skip_context7=skip_context7,
            )

            # Record bypass in implementation report if used
            if context7_bypassed:
                _record_context7_bypass(record_id, project_root)

            output_data = {
                "record_id": record_id,
                "ready": True,
                "state": task_entity.state,
                "session_id": session_id,
            }
            if context7_bypassed:
                output_data["context7_bypassed"] = True

            formatter.json_output(output_data) if formatter.json_mode else formatter.text(
                f"Task {record_id} marked as ready (moved to {task_entity.state})."
            )
            return 0

        else:
            # List all ready tasks (derived from dependency graph, not just todo state).
            from edison.core.task.readiness import TaskReadinessEvaluator

            # Listing is global by default. Only filter to a specific session when the user
            # explicitly requests it via --session.
            session_id = (
                resolve_session_id(project_root=project_root, explicit=args.session, required=False)
                if args.session
                else None
            )

            evaluator = TaskReadinessEvaluator(project_root=project_root)
            ready_tasks = [r.to_ready_list_dict() for r in evaluator.list_ready_tasks(session_id=session_id)]

            if ready_tasks:
                limit = 25
                shown = ready_tasks[:limit]
                list_text = f"Ready tasks ({len(ready_tasks)}):\n" + "\n".join(
                    f"  - {t['id']}: {t['title']}" for t in shown
                )
                if len(ready_tasks) > limit:
                    list_text += f"\n  ... and {len(ready_tasks) - limit} more (use --json for full list)"
            else:
                list_text = "No tasks ready to claim."

            if formatter.json_mode:
                formatter.json_output({"tasks": ready_tasks, "count": len(ready_tasks), "session_id": session_id})
            else:
                formatter.text(list_text)

            return 0

    except Exception as e:
        formatter.error(e, error_code="ready_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
