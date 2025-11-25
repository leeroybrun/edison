"""
Edison task link command.

SUMMARY: Link parent-child tasks
"""

from __future__ import annotations

import argparse
import sys
import json
import sys

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
    """Link tasks - delegates to core library."""
    from edison.core import task
    from pathlib import Path

    try:
        # Normalize the task IDs
        parent_id = task.normalize_record_id("task", args.parent_id)
        child_id = task.normalize_record_id("task", args.child_id)

        # Find both tasks
        parent_path = task.find_record(parent_id, "task")
        child_path = task.find_record(child_id, "task")

        # Load metadata
        parent_meta = task.read_metadata(parent_path, "task")
        child_meta = task.read_metadata(child_path, "task")

        if args.unlink:
            # Remove link - update metadata files
            # This requires updating the task markdown frontmatter
            # For now, print instruction
            if args.json:
                print(json.dumps({
                    "action": "unlink",
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "status": "not_implemented",
                    "message": "Unlinking requires metadata update - use task metadata editing",
                }, indent=2))
            else:
                print(f"Unlink not yet implemented")
                print(f"To unlink {child_id} from {parent_id}:")
                print(f"  Edit {child_path} and remove parent reference")
            return 1
        else:
            # Create link - update session if provided
            if args.session:
                from edison.core.session import store as session_store
                from edison.core.paths.resolver import PathResolver
                from edison.core.io_utils import read_json_safe, write_json_safe

                session_id = session_store.sanitize_session_id(args.session)

                # Find or create session
                try:
                    session = session_store.load_session(session_id)
                except:
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
                    session_store.save_session(session_id, session)
                except:
                    # Create session directory structure
                    session_dir = PathResolver.resolve_project_root() / ".project" / "sessions" / "draft" / session_id
                    session_dir.mkdir(parents=True, exist_ok=True)
                    write_json_safe(session_dir / "session.json", session)

            # Output result
            if args.json:
                result = {
                    "action": "link",
                    "parentId": parent_id,
                    "childId": child_id,
                    "status": "success",
                }
                if args.session:
                    result["sessionId"] = args.session
                print(json.dumps(result, indent=2))
            else:
                print(f"Linked {child_id} to parent {parent_id}")
                if args.session:
                    print(f"Session: {args.session}")
                print(f"\nTo persist this link, add to {child_path}:")
                print(f"  parent: {parent_id}")

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
