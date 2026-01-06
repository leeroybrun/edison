"""Prepare a new QA evidence round.

Creates a new `round-N/` directory for the resolved bundle root task and
initializes the round-scoped artifacts that validators depend on.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root, resolve_session_id
from edison.cli._worktree_enforcement import maybe_enforce_session_worktree
from edison.core.qa.evidence import EvidenceService
from edison.core.qa.workflow.repository import QARepository

SUMMARY = "Prepare a new QA evidence round (creates round-N and initializes reports)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier (root or bundle member)")
    parser.add_argument(
        "--scope",
        choices=["auto", "hierarchy", "bundle"],
        help="Validation scope used to resolve the bundle root (default: config or auto)",
    )
    parser.add_argument("--session", type=str, help="Session ID context (optional)")
    parser.add_argument(
        "--status",
        type=str,
        default="pending",
        help="Initial round status to append to the QA record (default: pending)",
    )
    parser.add_argument("--note", type=str, help="Notes for the round record (optional)")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        blocked = maybe_enforce_session_worktree(
            project_root=repo_root,
            command_name="qa round prepare",
            args=args,
            json_mode=bool(formatter.json_mode),
        )
        if blocked is not None:
            return int(blocked)

        session_id = resolve_session_id(project_root=repo_root, explicit=args.session, required=False)

        from edison.core.qa.bundler import build_validation_manifest

        manifest = build_validation_manifest(
            str(args.task_id),
            scope=getattr(args, "scope", None),
            project_root=repo_root,
            session_id=session_id,
        )
        root_task_id = str(manifest.get("rootTask") or args.task_id)
        scope_used = str(manifest.get("scope") or "hierarchy")
        manifest_tasks = list(manifest.get("tasks") or [])
        cluster_task_ids = [
            str(t.get("taskId") or "")
            for t in (manifest_tasks or [])
            if isinstance(t, dict) and t.get("taskId")
        ]

        qa_repo = QARepository(project_root=repo_root)
        qa_id = f"{root_task_id}-qa"

        try:
            updated = qa_repo.append_round(
                qa_id,
                status=str(args.status or "pending"),
                notes=getattr(args, "note", None),
                create_evidence_dir=True,
            )
        except Exception as e:
            formatter.error(
                f"Cannot append round to QA record '{qa_id}': {e}. Create the QA first (e.g. `edison qa new {root_task_id}`).",
                error_code="qa_missing",
            )
            return 1

        round_num = int(getattr(updated, "round", 0) or 0)
        if not round_num:
            formatter.error("Failed to allocate a round number", error_code="round_alloc")
            return 1

        ev = EvidenceService(root_task_id, project_root=repo_root)
        round_dir = ev.ensure_round(round_num)

        # Initialize implementation report (validators often depend on it for file-scoped context).
        existing_impl: dict[str, Any] = ev.read_implementation_report(round_num) or {}
        if not existing_impl:
            ev.write_implementation_report(
                {
                    "taskId": root_task_id,
                    "round": int(round_num),
                    "completionStatus": "partial",
                    "followUpTasks": [],
                    "notesForValidator": "",
                },
                round_num=round_num,
            )

        # Initialize a draft validation summary (primarily as a discoverable anchor).
        existing_summary: dict[str, Any] = ev.read_bundle(round_num) or {}
        if not existing_summary:
            from edison.core.utils.time import utc_timestamp

            ev.write_bundle(
                {
                    "taskId": root_task_id,
                    "rootTask": root_task_id,
                    "scope": scope_used,
                    "round": int(round_num),
                    "approved": False,
                    "generatedAt": utc_timestamp(),
                    "tasks": [{**t, "approved": False} for t in (manifest_tasks or []) if isinstance(t, dict)],
                    "validators": [],
                    "missing": [],
                    "nonBlockingFollowUps": [],
                },
                round_num=round_num,
            )

        if formatter.json_mode:
            formatter.json_output(
                {
                    "taskId": str(args.task_id),
                    "rootTask": root_task_id,
                    "scope": scope_used,
                    "clusterTaskIds": [t for t in cluster_task_ids if t],
                    "round": round_num,
                    "evidenceDir": str(round_dir.relative_to(repo_root)),
                    "implementationReport": str((round_dir / ev.implementation_filename).relative_to(repo_root)),
                    "validationSummary": str((round_dir / ev.bundle_filename).relative_to(repo_root)),
                }
            )
        else:
            formatter.text(f"Prepared round {round_num} for {root_task_id} (scope={scope_used}).")
            formatter.text(f"  Evidence: {round_dir.relative_to(repo_root)}")
            formatter.text("")
            formatter.text("Next steps:")
            formatter.text(f"  edison evidence capture {root_task_id}")
            formatter.text(f"  edison qa validate {args.task_id} --execute --round {round_num}")

        return 0
    except Exception as e:
        formatter.error(e, error_code="round_prepare_error")
        return 1

