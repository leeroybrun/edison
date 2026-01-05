"""
Edison qa new command.

SUMMARY: Ensure QA record exists for a task
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root, resolve_session_id
from edison.core.qa.workflow.repository import QARepository
from edison.core.task.workflow import TaskQAWorkflow

SUMMARY = "Ensure QA record exists for a task"


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
        help="QA owner/validator (default: _unassigned_)",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Ensure QA record exists for a task (creates if missing)."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        session_id = resolve_session_id(project_root=repo_root, explicit=args.session, required=False)

        from edison.cli import format_display_path, resolve_existing_task_id

        task_id = str(args.task_id)

        # Canonical ID semantics:
        # - CLI takes a task_id, but QA entity IDs are stored as "<task_id>-qa" (or "<task_id>.qa").
        if task_id.endswith("-qa") or task_id.endswith(".qa"):
            task_id = task_id[:-3]

        task_id = resolve_existing_task_id(project_root=repo_root, raw_task_id=task_id)
        qa_id = f"{task_id}-qa"

        workflow = TaskQAWorkflow(project_root=repo_root)
        qa_repo = QARepository(project_root=repo_root)
        qa_existed_before = qa_repo.get(qa_id) is not None

        qa = workflow.ensure_qa(
            task_id=task_id,
            session_id=session_id,
            validator_owner=str(args.owner) if args.owner else None,
            title=None,
        )

        qa_path = qa_repo.get_path(qa_id)
        qa_path_display = format_display_path(project_root=repo_root, path=qa_path)

        from edison.core.qa.workflow.next_steps import (
            build_qa_next_steps_payload,
            format_qa_next_steps_text,
        )

        qa_payload = build_qa_next_steps_payload(
            qa_id=qa.id,
            qa_state=str(qa.state),
            qa_path=qa_path_display,
            created=not qa_existed_before,
        )

        result = {
            "status": "ok",
            "task_id": task_id,
            "qa_id": qa.id,
            "state": qa.state,
            "validator_owner": qa.validator_owner,
            "session_id": qa.session_id,
            **qa_payload,
        }

        formatter.json_output(result) if formatter.json_mode else formatter.text(format_qa_next_steps_text(qa_payload))
        if not formatter.json_mode:
            try:
                from edison.core.artifacts import format_required_fill_next_steps_for_file

                hint = format_required_fill_next_steps_for_file(qa_path, display_path=str(qa_path_display))
                if hint:
                    formatter.text("")
                    formatter.text(hint)
            except Exception:
                # Fail-open: post-create UX helpers must not break QA creation.
                pass

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
