"""
Edison session show command.

SUMMARY: Show raw session JSON
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Show raw session JSON"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "session_id",
        help="Session identifier (e.g., sess-001)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)

        from edison.core.session.core.id import validate_session_id
        from edison.core.session.persistence.repository import SessionRepository

        session_id = validate_session_id(str(args.session_id))
        repo = SessionRepository(project_root=project_root)
        path = repo.get_path(session_id)
        content = path.read_text(encoding="utf-8", errors="strict")

        session = repo.get(session_id)
        if not session:
            raise FileNotFoundError(f"Session {session_id} not found")

        if formatter.json_mode:
            formatter.json_output(
                {
                    "recordType": "session",
                    "id": session_id,
                    "path": str(path),
                    "session": session.to_dict(),
                    "content": content,
                }
            )
        else:
            formatter.text(content)
        return 0
    except Exception as e:
        formatter.error(e, error_code="session_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

