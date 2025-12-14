"""
Edison qa bundle command.

SUMMARY: Emit a validation bundle manifest for a task cluster
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import add_json_flag, add_repo_root_flag, OutputFormatter, get_repo_root

SUMMARY = "Emit a validation bundle manifest for a task cluster"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Root task identifier for the cluster to validate",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context (recommended). If omitted, uses current session if available.",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Emit validation bundle manifest - single source is task/QA files + TaskIndex."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Resolve repo root early (ensures PathResolver has a stable cwd when used).
        _repo_root = get_repo_root(args)
        _ = _repo_root  # explicit: currently unused; kept for symmetry with other CLIs

        # Resolve session context (optional but recommended).
        session_id = getattr(args, "session", None)
        if not session_id:
            try:
                from edison.core.session import lifecycle as session_manager
                session_id = session_manager.get_current_session()
            except Exception:
                session_id = None

        if not session_id:
            formatter.error(
                "No session provided and no current session detected. Provide --session.",
                error_code="missing_session",
            )
            return 1

        from edison.core.session.persistence import graph as session_graph

        manifest = session_graph.build_validation_bundle(session_id=session_id, root_task=args.task_id)

        formatter.json_output(manifest) if formatter.json_mode else formatter.text(
            f"Bundle manifest for {args.task_id} (session {session_id})\n"
            f"  Tasks: {len(manifest.get('tasks', []) or [])}"
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="bundle_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
