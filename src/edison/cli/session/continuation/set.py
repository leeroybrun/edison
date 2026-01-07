"""
Edison session continuation set command.

SUMMARY: Set per-session continuation override in session metadata
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.session.core.id import validate_session_id
from edison.core.session.persistence.repository import SessionRepository

SUMMARY = "Set per-session continuation override in session metadata"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", help="Session identifier")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["off", "soft", "hard"],
        help="Continuation enforcement mode for this session",
    )
    parser.add_argument("--max-iterations", type=int, help="Override max iteration budget (>= 1)")
    parser.add_argument("--cooldown-seconds", type=int, help="Override cooldown seconds between injections (>= 0)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stop-on-blocked", action="store_true", help="Stop continuation when session is blocked")
    group.add_argument("--no-stop-on-blocked", action="store_true", help="Do not stop continuation when session is blocked")
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

        override: dict[str, object] = {"mode": str(args.mode)}
        if args.max_iterations is not None:
            if int(args.max_iterations) < 1:
                raise ValueError("--max-iterations must be >= 1")
            override["maxIterations"] = int(args.max_iterations)
        if args.cooldown_seconds is not None:
            if int(args.cooldown_seconds) < 0:
                raise ValueError("--cooldown-seconds must be >= 0")
            override["cooldownSeconds"] = int(args.cooldown_seconds)
        if bool(getattr(args, "stop_on_blocked", False)):
            override["stopOnBlocked"] = True
        if bool(getattr(args, "no_stop_on_blocked", False)):
            override["stopOnBlocked"] = False

        if not isinstance(session.meta_extra, dict):
            session.meta_extra = {}
        session.meta_extra["continuation"] = override
        session.add_activity("Session continuation override updated")
        repo.save(session)

        if formatter.json_mode:
            formatter.json_output({"status": "ok", "sessionId": session_id, "continuation": override})
        else:
            formatter.text(f"Updated session continuation override for {session_id}")
        return 0
    except Exception as e:
        formatter.error(e, error_code="session_continuation_set_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

