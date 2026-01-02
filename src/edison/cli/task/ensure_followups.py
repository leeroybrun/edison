"""
Edison task ensure_followups command.

SUMMARY: Generate required follow-up tasks
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task import TaskRepository, TaskQAWorkflow, normalize_record_id
from edison.core.session import validate_session_id

SUMMARY = "Generate required follow-up tasks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task ID to generate follow-ups for",
    )
    parser.add_argument(
        "--session",
        help="Session ID for context",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview follow-ups without creating them",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip pre-create duplicate checks (if configured)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Ensure follow-ups - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize the task ID
        task_id = normalize_record_id("task", args.task_id)

        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = validate_session_id(args.session)

        # Find the task using repository
        task_repo = TaskRepository(project_root=project_root)
        task_entity = task_repo.get(task_id)
        if not task_entity:
            raise ValueError(f"Task not found: {task_id}")

        # Get task title for rule matching
        task_title = task_entity.title.lower() if task_entity.title else ""

        # Determine what follow-ups are needed
        # This is domain-specific logic - for now, implement basic rules
        followups = []

        # Rule 1: If task modified schema, need migration task
        if "schema" in task_title or "database" in task_title:
            followups.append({
                "type": "migration",
                "title": f"Migration for {task_id}",
                "reason": "Database schema changes require migration",
            })

        # Rule 2: If task added API, need tests
        if "api" in task_title or "endpoint" in task_title:
            followups.append({
                "type": "test",
                "title": f"Tests for {task_id}",
                "reason": "New API endpoints require test coverage",
            })

        # Rule 3: If task added UI component, need integration test
        if "component" in task_title or "ui" in task_title:
            followups.append({
                "type": "test",
                "title": f"Integration tests for {task_id}",
                "reason": "New UI components require integration tests",
            })

        if args.dry_run:
            if followups:
                dry_run_text = f"Would create {len(followups)} follow-up task(s) for {task_id}:\n" + "\n".join(
                    f"  - {fu['title']} ({fu['type']})\n    Reason: {fu['reason']}" for fu in followups
                )
            else:
                dry_run_text = f"No follow-ups needed for {task_id}"

            formatter.json_output({
                "dry_run": True,
                "task_id": task_id,
                "followups": followups,
                "count": len(followups),
            }) if formatter.json_mode else formatter.text(dry_run_text)
            return 0

        # Create follow-up tasks using workflow
        workflow = TaskQAWorkflow(project_root=project_root)
        created = []
        for i, fu in enumerate(followups):
            # Generate child ID based on parent
            child_id = f"{task_id}.{i+1}-followup"
            description = f"{fu['reason']}\nParent: {task_id}"

            duplicates = []
            if not bool(getattr(args, "force", False)):
                try:
                    from edison.core.task.duplication import DuplicateTaskError, check_duplicates_or_raise

                    duplicates = check_duplicates_or_raise(
                        title=str(fu.get("title") or ""),
                        description=str(description),
                        project_root=project_root,
                    )
                except DuplicateTaskError as exc:
                    if formatter.json_mode:
                        formatter.json_output(
                            {
                                "error": "duplicate_task",
                                "message": str(exc),
                                "duplicates": [
                                    {
                                        "taskId": m.task_id,
                                        "score": round(m.score, 2),
                                        "title": m.title,
                                        "state": m.state,
                                    }
                                    for m in exc.matches
                                ],
                                "proposedTaskId": child_id,
                            }
                        )
                    else:
                        formatter.error(exc, error_code="duplicate_task")
                    return 1
                except Exception:
                    duplicates = []

            if duplicates and not formatter.json_mode:
                formatter.text(f"Possible duplicates for {child_id} ({len(duplicates)}):")
                for m in duplicates:
                    formatter.text(f"- {m.task_id}: {round(m.score, 2)} — {m.title}")
                formatter.text("")

            workflow.create_task(
                task_id=child_id,
                title=fu["title"],
                description=description,
                session_id=session_id or task_entity.session_id,
                create_qa=True,
            )
            created.append({
                "id": child_id,
                "type": fu["type"],
                "title": fu["title"],
                **(
                    {
                        "duplicates": [
                            {
                                "taskId": m.task_id,
                                "score": round(m.score, 2),
                                "title": m.title,
                                "state": m.state,
                            }
                            for m in duplicates
                        ]
                    }
                    if duplicates
                    else {}
                ),
            })

        if created:
            result_text = f"Created {len(created)} follow-up task(s) for {task_id}:\n" + "\n".join(
                f"  - {fu['id']}: {fu['title']}" for fu in created
            )
        else:
            result_text = f"No follow-ups needed for {task_id}"

        formatter.json_output({
            "status": "created",
            "task_id": task_id,
            "followups": created,
            "count": len(created),
        }) if formatter.json_mode else formatter.text(result_text)

        if created and not formatter.json_mode:
            try:
                from edison.core.artifacts import format_required_fill_next_steps_for_file

                for fu in created:
                    followup_id = fu.get("id") if isinstance(fu, dict) else None
                    if not followup_id:
                        continue
                    try:
                        followup_path = task_repo.get_path(str(followup_id))
                        rel_path = (
                            followup_path.relative_to(project_root)
                            if followup_path.is_relative_to(project_root)
                            else followup_path
                        )
                        hint = format_required_fill_next_steps_for_file(
                            followup_path, display_path=str(rel_path)
                        )
                        if hint:
                            formatter.text("")
                            formatter.text(hint)
                    except Exception:
                        continue
            except Exception:
                pass

        return 0

    except Exception as e:
        formatter.error(e, error_code="followup_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
