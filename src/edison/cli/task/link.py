"""
Edison task link command.

SUMMARY: Link parent-child tasks
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root
from edison.core.task import TaskRepository, normalize_record_id
from edison.core.session import validate_session_id
from edison.core.utils.io import write_json_atomic
from edison.core.session.core.models import Session

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
        help="Session ID to associate the link with",
    )
    parser.add_argument(
        "--unlink",
        action="store_true",
        help="Remove link instead of creating it",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Link tasks - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        # Resolve project root
        project_root = get_repo_root(args)

        # Normalize the task IDs
        parent_id = normalize_record_id("task", args.parent_id)
        child_id = normalize_record_id("task", args.child_id)

        # Get both tasks using repository
        task_repo = TaskRepository(project_root=project_root)
        parent_entity = task_repo.get(parent_id)
        child_entity = task_repo.get(child_id)

        if not parent_entity:
            raise ValueError(f"Parent task not found: {parent_id}")
        if not child_entity:
            raise ValueError(f"Child task not found: {child_id}")

        if args.unlink:
            # Remove link - update metadata files
            # This requires updating the task markdown frontmatter
            # For now, print instruction
            formatter.json_output({
                "action": "unlink",
                "parent_id": parent_id,
                "child_id": child_id,
                "status": "not_implemented",
                "message": "Unlinking requires metadata update - use task metadata editing",
            }) if formatter.json_mode else formatter.text(
                f"Unlink not yet implemented\n"
                f"To unlink {child_id} from {parent_id}:\n"
                f"  Edit the child task file and remove parent reference"
            )
            return 1
        else:
            # Create link - update session if provided
            if args.session:
                from edison.core.session.persistence.repository import SessionRepository

                session_id = validate_session_id(args.session)

                # Find or create session
                session_repo = SessionRepository(project_root=project_root)
                session_entity = session_repo.get(session_id)

                if session_entity:
                    session = session_entity.to_dict()
                else:
                    # Create new session in draft state
                    session = {
                        "id": session_id,
                        "state": "draft",
                        "meta": {
                            "sessionId": session_id,
                            "createdAt": "2000-01-01T00:00:00Z",
                        },
                        "tasks": {},
                        "qa": {},
                        "activityLog": [],
                    }

                # Update task graph
                session.setdefault("tasks", {})
                session["tasks"][parent_id] = session["tasks"].get(parent_id, {})
                session["tasks"][child_id] = {
                    "parentId": parent_id,
                }

                # Save session
                try:
                    session_entity = Session.from_dict(session)
                    session_repo.save(session_entity)
                except:
                    # Create session directory structure
                    session_dir = project_root / ".project" / "sessions" / "draft" / session_id
                    session_dir.mkdir(parents=True, exist_ok=True)
                    write_json_atomic(session_dir / "session.json", session)

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
                link_text += f"\nSession: {args.session}"
            link_text += f"\n\nTo persist this link, add to the child task file:\n  parent: {parent_id}"

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
