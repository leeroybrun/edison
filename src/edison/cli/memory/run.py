"""
Edison memory run command.

SUMMARY: Run configured memory pipelines for an event
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root, resolve_session_id

SUMMARY = "Run configured memory pipelines for an event"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--event", required=True, help="Pipeline event id (e.g., session-end)")
    parser.add_argument(
        "--session",
        help="Optional session id (defaults to auto-detected current session if available)",
    )
    parser.add_argument(
        "--best-effort",
        action="store_true",
        help="Never fail the command due to config/provider errors (hooks-friendly)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        session_id = resolve_session_id(
            project_root=project_root,
            explicit=getattr(args, "session", None),
            required=False,
        )
        if not session_id:
            raise ValueError("No session id available (pass --session or run inside a session)")

        from edison.core.memory.pipeline import run_memory_pipelines

        strict = not bool(getattr(args, "best_effort", False))
        run_memory_pipelines(
            project_root=project_root,
            event=str(args.event),
            session_id=str(session_id),
            strict=strict,
        )

        payload = {"ran": True, "event": str(args.event), "sessionId": str(session_id)}
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            formatter.text("OK")
        return 0
    except Exception as exc:
        if bool(getattr(args, "best_effort", False)):
            payload = {"ran": False, "bestEffort": True, "error": str(exc)}
            if formatter.json_mode:
                formatter.json_output(payload)
            else:
                formatter.text("")
            return 0

        formatter.error(exc, error_code="memory_run_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

