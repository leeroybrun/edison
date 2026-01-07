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
    resolve_existing_task_id,
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
        raw_task_id = str(args.task_id)
        try:
            args.task_id = resolve_existing_task_id(project_root=repo_root, raw_task_id=raw_task_id)
        except Exception:
            args.task_id = raw_task_id
        if str(args.task_id) != raw_task_id and not formatter.json_mode:
            print(f"Resolved task id '{raw_task_id}' -> '{args.task_id}'", file=sys.stderr)

        from edison.core.qa.bundler import build_validation_manifest
        from edison.core.qa.evidence import EvidenceService, rounds
        from edison.core.qa.workflow.next_steps import build_bundle_next_steps_payload, format_bundle_next_steps_text
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
        validation_summary_path = round_dir / ev.bundle_filename

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

        guidance = build_bundle_next_steps_payload(manifest=manifest, project_root=repo_root)

        if formatter.json_mode:
            out = dict(manifest)
            out.update(
                {
                    "round": round_num,
                    "validationSummary": str(validation_summary_path.relative_to(repo_root)),
                    "nextSteps": guidance.get("nextSteps") or [],
                    "bundleReports": guidance.get("bundleReports") or {},
                }
            )
            formatter.json_output(out)
        else:
            formatter.text(
                f"Bundle manifest for {args.task_id}"
                + (f" (session {session_id})" if session_id else "")
                + "\n"
                f"  Root: {root_task} (scope={scope_used})\n"
                f"  Tasks: {len(manifest.get('tasks', []) or [])}\n"
                f"  Validation summary: {validation_summary_path.relative_to(repo_root)}"
            )
            formatter.text("")
            formatter.text(format_bundle_next_steps_text(guidance))

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
