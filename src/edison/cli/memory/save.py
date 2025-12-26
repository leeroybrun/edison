"""
Edison memory save command.

SUMMARY: Save a session summary to configured long-term memory providers
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root, resolve_session_id

SUMMARY = "Save a session summary to configured long-term memory providers"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("summary", help="Session summary text (or a compact record)")
    parser.add_argument(
        "--session",
        help="Optional session id to associate with the summary (defaults to current session if available)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        session_id = resolve_session_id(
            project_root=project_root, explicit=getattr(args, "session", None), required=False
        )
        from edison.core.memory import MemoryManager

        mgr = MemoryManager(project_root=project_root, validate_config=True)
        mgr.save(str(args.summary), session_id=session_id)
        payload = {"saved": True, "sessionId": session_id}
        formatter.json_output(payload) if formatter.json_mode else formatter.text("Saved.")
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="memory_save_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
