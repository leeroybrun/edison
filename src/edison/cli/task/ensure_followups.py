"""
Edison task ensure_followups command.

SUMMARY: Generate required follow-up tasks
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

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
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Ensure follow-ups - delegates to core library."""
    from edison.core import task
    from edison.core.session import store as session_store

    try:
        # Normalize the task ID
        task_id = task.normalize_record_id("task", args.task_id)

        # Normalize session ID if provided
        session_id = None
        if args.session:
            session_id = session_store.validate_session_id(args.session)

        # Find the task
        task_path = task.find_record(task_id, "task")
        metadata = task.read_metadata(task_path, "task")

        # Determine what follow-ups are needed
        # This is domain-specific logic - for now, implement basic rules
        followups = []

        # Rule 1: If task modified schema, need migration task
        if "schema" in metadata.title.lower() or "database" in metadata.title.lower():
            followups.append({
                "type": "migration",
                "title": f"Migration for {task_id}",
                "reason": "Database schema changes require migration",
            })

        # Rule 2: If task added API, need tests
        if "api" in metadata.title.lower() or "endpoint" in metadata.title.lower():
            followups.append({
                "type": "test",
                "title": f"Tests for {task_id}",
                "reason": "New API endpoints require test coverage",
            })

        # Rule 3: If task added UI component, need integration test
        if "component" in metadata.title.lower() or "ui" in metadata.title.lower():
            followups.append({
                "type": "test",
                "title": f"Integration tests for {task_id}",
                "reason": "New UI components require integration tests",
            })

        if args.dry_run:
            if args.json:
                print(json.dumps({
                    "dry_run": True,
                    "task_id": task_id,
                    "followups": followups,
                    "count": len(followups),
                }, indent=2))
            else:
                if followups:
                    print(f"Would create {len(followups)} follow-up task(s) for {task_id}:")
                    for fu in followups:
                        print(f"  - {fu['title']} ({fu['type']})")
                        print(f"    Reason: {fu['reason']}")
                else:
                    print(f"No follow-ups needed for {task_id}")
            return 0

        # Create follow-up tasks
        created = []
        for fu in followups:
            child_id = task.next_child_id(task_id)
            # create_task signature: task_id, title, description
            description = f"{fu['reason']}\nParent: {task_id}"
            child_path = task.create_task(
                task_id=child_id,
                title=fu["title"],
                description=description,
            )
            created.append({
                "id": child_id,
                "type": fu["type"],
                "title": fu["title"],
            })

        if args.json:
            print(json.dumps({
                "status": "created",
                "task_id": task_id,
                "followups": created,
                "count": len(created),
            }, indent=2))
        else:
            if created:
                print(f"Created {len(created)} follow-up task(s) for {task_id}:")
                for fu in created:
                    print(f"  - {fu['id']}: {fu['title']}")
            else:
                print(f"No follow-ups needed for {task_id}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, file=sys.stderr, indent=2))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
