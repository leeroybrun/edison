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

        from edison.core.task import normalize_record_id

        task_id = str(args.task_id)

        # Canonical ID semantics:
        # - CLI takes a task_id, but QA entity IDs are stored as "<task_id>-qa" (or "<task_id>.qa").
        if task_id.endswith("-qa") or task_id.endswith(".qa"):
            task_id = task_id[:-3]

        task_id = normalize_record_id("task", task_id)
        qa_id = f"{task_id}-qa"

        workflow = TaskQAWorkflow(project_root=repo_root)
        qa = workflow.ensure_qa(
            task_id=task_id,
            session_id=session_id,
            validator_owner=str(args.owner) if args.owner else None,
            title=None,
        )

        qa_repo = QARepository(project_root=repo_root)
        qa_path = qa_repo.get_path(qa_id)
        rel_path = qa_path.relative_to(repo_root) if qa_path.is_relative_to(repo_root) else qa_path

        result = {
            "status": "ok",
            "task_id": task_id,
            "qa_id": qa.id,
            "state": qa.state,
            "validator_owner": qa.validator_owner,
            "session_id": qa.session_id,
            "qaPath": str(rel_path),
        }

        formatter.json_output(result) if formatter.json_mode else formatter.text(
            f"QA ready: {qa_id} ({qa.state})\n  @{rel_path}"
        )
        if not formatter.json_mode:
            try:
                from edison.core.artifacts import format_required_fill_next_steps_for_file

                hint = format_required_fill_next_steps_for_file(qa_path, display_path=str(rel_path))
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
