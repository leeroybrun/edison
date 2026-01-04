"""
Edison task link command.

SUMMARY: Link parent-child tasks

Links are stored in task entities (canonical `relationships:` edges),
NOT in session JSON. This is the single source of truth.
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task import TaskRepository, normalize_record_id

SUMMARY = "Link parent-child tasks"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "parent_id",
        help="Parent task ID",
    )
    parser.add_argument(
        "child_id",
        help="Child task ID",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID context (optional - links are stored in task files)",
    )
    parser.add_argument(
        "--unlink",
        action="store_true",
        help="Remove link instead of creating it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing links or creating cycles",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Link tasks - stores relationships in task entities (single source of truth)."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize the task IDs
        parent_id = normalize_record_id("task", args.parent_id)
        child_id = normalize_record_id("task", args.child_id)

        # Get both tasks using repository (for graph validation).
        task_repo = TaskRepository(project_root=project_root)
        parent_task = task_repo.get(parent_id)
        child_task = task_repo.get(child_id)

        if not parent_task:
            raise ValueError(f"Parent task not found: {parent_id}")
        if not child_task:
            raise ValueError(f"Child task not found: {child_id}")

        if args.unlink:
            from edison.core.task.relationships.service import TaskRelationshipService

            TaskRelationshipService(project_root=project_root).remove(
                task_id=child_id,
                rel_type="parent",
                target_id=parent_id,
            )
            
            result = {
                "action": "unlink",
                "parentId": parent_id,
                "childId": child_id,
                "status": "success",
            }
            
            formatter.json_output(result) if formatter.json_mode else formatter.text(
                f"Unlinked {child_id} from parent {parent_id}"
            )
        else:
            if parent_id == child_id:
                raise ValueError("Cannot link a task to itself")

            # Prevent cycles + overwrites unless --force.
            # A cycle would be created if the proposed parent is already a descendant
            # of the child (i.e., walking parent->parent_id reaches the child).
            if child_task.parent_id and child_task.parent_id != parent_id and not args.force:
                raise ValueError(
                    f"Child task {child_id} already has parent {child_task.parent_id}; "
                    "use --force to overwrite"
                )

            cur = parent_task
            seen: set[str] = set()
            while cur and cur.parent_id:
                pid = str(cur.parent_id)
                if pid in seen:
                    # Corrupt existing graph; fail closed unless forced.
                    if not args.force:
                        raise ValueError(
                            f"Cycle detected while checking ancestry of {parent_id}; use --force to proceed"
                        )
                    break
                seen.add(pid)
                if pid == child_id:
                    if not args.force:
                        raise ValueError(
                            f"Cycle detected: linking {parent_id} -> {child_id} would create a loop; "
                            "use --force to proceed"
                        )
                    break
                cur = task_repo.get(pid)

            from edison.core.task.relationships.service import TaskRelationshipService

            TaskRelationshipService(project_root=project_root).add(
                task_id=child_id,
                rel_type="parent",
                target_id=parent_id,
                force=bool(getattr(args, "force", False)),
            )

            # Output result
            result = {
                "action": "link",
                "parentId": parent_id,
                "childId": child_id,
                "status": "success",
            }
            if args.session:
                result["sessionId"] = args.session

            link_text = f"Linked {child_id} to parent {parent_id}"
            if args.session:
                link_text += f"\nSession context: {args.session}"

            formatter.json_output(result) if formatter.json_mode else formatter.text(link_text)

        return 0

    except Exception as e:
        formatter.error(e, error_code="link_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
