"""
Edison qa bundle command.

SUMMARY: Emit a validation bundle manifest for a task cluster
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_session_id,
)

SUMMARY = "Emit a validation bundle manifest for a task cluster"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Root task identifier for the cluster to validate",
    )
    parser.add_argument(
        "--scope",
        choices=["auto", "hierarchy", "bundle"],
        help="Cluster selection scope (default: config or auto)",
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
        repo_root = get_repo_root(args)

        # Resolve session context (optional but recommended).
        session_id = resolve_session_id(
            project_root=repo_root,
            explicit=getattr(args, "session", None),
            required=False,
        )
        from edison.core.qa.bundler import build_validation_manifest
        from edison.core.qa.evidence import EvidenceService, rounds
        from edison.core.utils.time import utc_timestamp

        manifest = build_validation_manifest(
            args.task_id,
            scope=getattr(args, "scope", None),
            project_root=repo_root,
            session_id=session_id,
        )

        root_task = str(manifest.get("rootTask") or args.task_id)
        scope_used = str(manifest.get("scope") or "").strip() or "hierarchy"

        ev = EvidenceService(root_task, project_root=repo_root)
        round_dir = ev.ensure_round()
        round_num = rounds.get_round_number(round_dir)

        # Persist a draft bundle summary with per-task approvals defaulting to false.
        bundle_data = {
            "taskId": root_task,
            "rootTask": root_task,
            "scope": scope_used,
            "round": round_num,
            "approved": False,
            "generatedAt": utc_timestamp(),
            "tasks": [{**t, "approved": False} for t in (manifest.get("tasks") or [])],
            "validators": [],
            "nonBlockingFollowUps": [],
        }
        ev.write_bundle(bundle_data, round_num=round_num)

        formatter.json_output(manifest) if formatter.json_mode else formatter.text(
            f"Bundle manifest for {args.task_id}"
            + (f" (session {session_id})" if session_id else "")
            + "\n"
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
