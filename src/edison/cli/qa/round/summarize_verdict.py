"""Summarize validation verdicts for an existing evidence round.

Reads existing validator reports in a round, computes overall approval, and
writes/updates `validation-summary.md` (mirrored into bundle members).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_existing_task_id,
    resolve_session_id,
)
from edison.cli._worktree_enforcement import maybe_enforce_session_worktree

SUMMARY = "Compute approval from existing reports and write validation-summary.md (no validator execution)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier (root or bundle member)")
    parser.add_argument(
        "--scope",
        choices=["auto", "hierarchy", "bundle"],
        help="Validation scope (default: config or auto)",
    )
    parser.add_argument("--session", type=str, help="Session ID context (optional)")
    parser.add_argument("--round", type=int, help="Evidence round number (default: current)")
    parser.add_argument("--preset", type=str, help="Preset override used for approval (optional)")
    parser.add_argument(
        "--add-validators",
        nargs="+",
        metavar="[WAVE:]VALIDATOR",
        help="Add extra validators (affects the blocking set used for approval)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        blocked = maybe_enforce_session_worktree(
            project_root=repo_root,
            command_name="qa round summarize-verdict",
            args=args,
            json_mode=bool(formatter.json_mode),
        )
        if blocked is not None:
            return int(blocked)

        session_id = resolve_session_id(project_root=repo_root, explicit=args.session, required=False)

        raw_task_id = str(args.task_id)
        try:
            args.task_id = resolve_existing_task_id(project_root=repo_root, raw_task_id=raw_task_id)
        except Exception:
            args.task_id = raw_task_id

        if str(args.task_id) != raw_task_id and not formatter.json_mode:
            print(f"Resolved task id '{raw_task_id}' -> '{args.task_id}'", file=sys.stderr)

        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(project_root=repo_root, max_workers=1)
        validator_registry = executor.get_validator_registry()

        extra_validators = None
        if getattr(args, "add_validators", None):
            extra_validators = validator_registry.parse_extra_validators(args.add_validators)

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

        from edison.core.qa.evidence import EvidenceService

        root_ev = EvidenceService(root_task_id, project_root=repo_root)

        from edison.core.qa.locks.task import acquire_qa_task_lock

        with acquire_qa_task_lock(
            project_root=repo_root,
            task_id=root_task_id,
            purpose="summarize",
            session_id=session_id,
            timeout_seconds=30.0,
        ):
            round_num = int(args.round or root_ev.get_current_round() or 0)
            if not round_num or not root_ev.get_round_dir(round_num).exists():
                formatter.error(
                    f"No evidence round found for {root_task_id}; run `edison qa round prepare {root_task_id}` first.",
                    error_code="no_round",
                )
                return 1

            roster = validator_registry.build_execution_roster(
                task_id=str(args.task_id),
                session_id=session_id,
                wave=None,
                extra_validators=extra_validators,
                preset_name=getattr(args, "preset", None),
            )
            preset_used = str(roster.get("preset") or getattr(args, "preset", None) or "").strip()

            # Reuse the single source of truth for approval computation + mirroring.
            from edison.cli.qa.validate import _compute_bundle_summary, _mirror_bundle_summary  # type: ignore

            bundle_data, overall_approved, cluster_missing = _compute_bundle_summary(
                args=args,
                repo_root=repo_root,
                session_id=session_id,
                validator_registry=validator_registry,
                round_num=round_num,
                extra_validators=extra_validators,
                execution_result=None,
                root_task_id=root_task_id,
                scope_used=scope_used,
                cluster_task_ids=cluster_task_ids,
                manifest_tasks=manifest_tasks,
                preset_used=preset_used,
            )

            root_ev.write_bundle(bundle_data, round_num=round_num)
            _mirror_bundle_summary(
                repo_root=repo_root,
                round_num=round_num,
                root_task_id=root_task_id,
                cluster_task_ids=cluster_task_ids,
                bundle_data=bundle_data,
            )

        if formatter.json_mode:
            formatter.json_output(
                {
                    "taskId": str(args.task_id),
                    "rootTask": root_task_id,
                    "scope": scope_used,
                    "round": round_num,
                    "preset": preset_used,
                    "approved": overall_approved,
                    "missing": bundle_data.get("missing") or [],
                    "cluster_missing": cluster_missing,
                    "summary_file": str((root_ev.get_round_dir(round_num) / root_ev.bundle_filename).relative_to(repo_root)),
                }
            )
        else:
            if overall_approved:
                formatter.text(f"Approved: all blocking reports approved; wrote {root_ev.bundle_filename}.")
            else:
                formatter.text("Not approved (missing or failing blocking reports).")
                for tid, missing in (cluster_missing or {}).items():
                    suffix = f": {', '.join(missing)}" if missing else ""
                    formatter.text(f"  - {tid}{suffix}")

        return 0 if overall_approved else 1
    except Exception as e:
        formatter.error(e, error_code="summarize_verdict_error")
        return 1


if __name__ == "__main__":
    import sys

    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))
