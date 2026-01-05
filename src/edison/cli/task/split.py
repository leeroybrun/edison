"""
Edison task split command.

SUMMARY: Split task into subtasks
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task import TaskRepository, TaskQAWorkflow, normalize_record_id

SUMMARY = "Split task into subtasks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task ID to split",
    )
    parser.add_argument(
        "--count",
        "--children",
        type=int,
        default=2,
        help="Number of subtasks to create (default: 2)",
    )
    parser.add_argument(
        "--prefix",
        help="Label for child task IDs (appended after '<parent>.<n>-')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview split without creating tasks",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip pre-create duplicate checks (if configured)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Split task - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize the task ID
        task_id = normalize_record_id("task", args.task_id)

        # Get the task using repository
        task_repo = TaskRepository(project_root=project_root)
        task_entity = task_repo.get(task_id)
        if not task_entity:
            raise ValueError(f"Task not found: {task_id}")

        # Generate child IDs
        next_child_id = task_repo.get_next_child_id(task_id)
        try:
            next_child_num = int(next_child_id.split(".", 1)[1])
        except Exception:
            raise ValueError(f"Invalid next child id format returned by repository: {next_child_id}")

        child_ids = []
        for offset in range(args.count):
            child_num = next_child_num + offset
            suffix = args.prefix if args.prefix else f"part{child_num}"
            child_id = f"{task_id}.{child_num}-{suffix}"
            child_ids.append(child_id)

        if args.dry_run:
            dry_run_text = f"Would split {task_id} into {args.count} subtasks:\n" + "\n".join(
                f"  - {child_id}" for child_id in child_ids
            )
            formatter.json_output({
                "dry_run": True,
                "parent_id": task_id,
                "child_ids": child_ids,
                "count": args.count,
            }) if formatter.json_mode else formatter.text(dry_run_text)
            return 0

        # Create child tasks using TaskQAWorkflow
        workflow = TaskQAWorkflow(project_root=project_root)
        created = []
        for i, child_id in enumerate(child_ids):
            # Create task with parent reference
            description = f"Subtask {i+1} of {args.count}\nParent: {task_id}"

            if not bool(getattr(args, "force", False)):
                try:
                    from edison.core.task.duplication import DuplicateTaskError, check_duplicates_or_raise

                    _ = check_duplicates_or_raise(
                        title=f"Part {child_id.split('.', 1)[1].split('-', 1)[0]}",
                        description=description,
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
                    pass

            workflow.create_task(
                task_id=child_id,
                title=f"Part {child_id.split('.', 1)[1].split('-', 1)[0]}",
                description=description,
                session_id=task_entity.session_id,
                create_qa=True,
            )
            created.append(child_id)

        # Persist parent/child links via the canonical relationship service (single source of truth).
        from edison.core.task.relationships.service import TaskRelationshipService

        rel_svc = TaskRelationshipService(project_root=project_root)
        for child_id in created:
            rel_svc.add(task_id=child_id, rel_type="parent", target_id=task_id)

        result_text = f"Split {task_id} into {len(created)} subtasks:\n" + "\n".join(
            f"  - {child_id}" for child_id in created
        )

        formatter.json_output({
            "status": "split",
            "parent_id": task_id,
            "child_ids": created,
            "count": len(created),
        }) if formatter.json_mode else formatter.text(result_text)

        if created and not formatter.json_mode:
            try:
                from edison.core.artifacts import format_required_fill_next_steps_for_file

                for child_id in created:
                    try:
                        child_path = task_repo.get_path(child_id)
                        rel_path = (
                            child_path.relative_to(project_root)
                            if child_path.is_relative_to(project_root)
                            else child_path
                        )
                        hint = format_required_fill_next_steps_for_file(child_path, display_path=str(rel_path))
                        if hint:
                            formatter.text("")
                            formatter.text(hint)
                    except Exception:
                        continue
            except Exception:
                pass

        return 0

    except Exception as e:
        formatter.error(e, error_code="split_error")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
