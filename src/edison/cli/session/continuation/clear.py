"""
Edison session continuation clear command.

SUMMARY: Clear per-session continuation override (fall back to project defaults)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.session.core.id import validate_session_id
from edison.core.session.persistence.repository import SessionRepository

SUMMARY = "Clear per-session continuation override (fall back to project defaults)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", help="Session identifier")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        session_id = validate_session_id(str(args.session_id))

        repo = SessionRepository(project_root=project_root)
        session = repo.get(session_id)
        if not session:
            raise FileNotFoundError(f"Session {session_id} not found")

        if isinstance(session.meta_extra, dict):
            session.meta_extra.pop("continuation", None)
        session.add_activity("Session continuation override cleared")
        repo.save(session)

        if formatter.json_mode:
            formatter.json_output({"status": "ok", "sessionId": session_id, "cleared": True})
        else:
            formatter.text(f"Cleared session continuation override for {session_id}")
        return 0
    except Exception as e:
        formatter.error(e, error_code="session_continuation_clear_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

