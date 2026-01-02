"""
Edison qa validate command.

SUMMARY: Run validators against a task bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    resolve_session_id,
)
from edison.cli._worktree_enforcement import maybe_enforce_session_worktree
from edison.core.qa.engines import ValidationExecutor
from edison.core.registries.validators import ValidatorRegistry

SUMMARY = "Run validators against a task bundle"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier to validate",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID context (optional)",
    )
    parser.add_argument(
        "--round",
        type=int,
        help="Validation round number (default: use current round; creates round-1 if none)",
    )
    parser.add_argument(
        "--new-round",
        action="store_true",
        help="Create a new evidence round directory and run validators in it",
    )
    parser.add_argument(
        "--wave",
        type=str,
        help="Specific wave to validate (e.g., critical, comprehensive)",
    )
    parser.add_argument(
        "--validators",
        nargs="+",
        help="Specific validator IDs to run (default: run all applicable)",
    )
    parser.add_argument(
        "--add-validators",
        nargs="+",
        metavar="[WAVE:]VALIDATOR",
        help="Add extra validators: 'react' (default wave) or 'critical:react' (specific wave)",
    )
    parser.add_argument(
        "--blocking-only",
        action="store_true",
        help="Only run blocking validators",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute validators directly (default: show roster only)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not execute validators; compute approval from existing evidence and emit the bundle summary file",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run validators sequentially instead of in parallel",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)",
    )
    parser.add_argument(
        "--worktree-path",
        type=str,
        metavar="PATH",
        help="Override worktree path for validation (advanced use: validate specific checkout)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Override timeout for all validators (seconds)",
    )
    parser.add_argument(
        "--timeout-multiplier",
        type=float,
        default=None,
        help="Multiply default validator timeouts by this factor",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run validators - delegates to core ValidationExecutor."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        blocked = maybe_enforce_session_worktree(
            project_root=repo_root,
            command_name="qa validate",
            args=args,
            json_mode=bool(formatter.json_mode),
        )
        if blocked is not None:
            return int(blocked)

        session_id = resolve_session_id(project_root=repo_root, explicit=args.session, required=False)
        if args.execute and args.check_only:
            raise ValueError("Pass only one of --execute or --check-only")

        # Create executor (centralized in core)
        executor = ValidationExecutor(
            project_root=repo_root,
            max_workers=args.max_workers,
        )
        # Use ValidatorRegistry (single source of truth) for roster building
        validator_registry = executor.get_validator_registry()

        # Build extra validators list from --add-validators using unified syntax
        extra_validators = None
        if getattr(args, "add_validators", None):
            extra_validators = validator_registry.parse_extra_validators(args.add_validators)

        # Build validator roster for display
        roster = validator_registry.build_execution_roster(
            task_id=args.task_id,
            session_id=session_id,
            wave=args.wave,
            extra_validators=extra_validators,
        )

        if args.blocking_only:
            roster["triggeredOptional"] = []

        # Filter to specific validators if requested
        if args.validators:
            roster = {
                "taskId": roster.get("taskId"),
                "modifiedFiles": roster.get("modifiedFiles", []),
                "alwaysRequired": [
                    v for v in roster.get("alwaysRequired", []) if v["id"] in args.validators
                ],
                "triggeredBlocking": [
                    v for v in roster.get("triggeredBlocking", []) if v["id"] in args.validators
                ],
                "triggeredOptional": [
                    v for v in roster.get("triggeredOptional", []) if v["id"] in args.validators
                ],
                "extraAdded": roster.get("extraAdded", []),
                "skipped": roster.get("skipped", []),
                "totalBlocking": 0,
                "decisionPoints": roster.get("decisionPoints", []),
            }
            roster["totalBlocking"] = len(roster["alwaysRequired"]) + len(roster["triggeredBlocking"])

        # Collect all validators to display
        validators_to_run = (
            roster.get("alwaysRequired", [])
            + roster.get("triggeredBlocking", [])
            + roster.get("triggeredOptional", [])
        )

        # Execute mode: use centralized executor
        if args.execute and not args.dry_run:
            return _execute_with_executor(
                args=args,
                repo_root=repo_root,
                executor=executor,
                formatter=formatter,
                session_id=session_id,
                extra_validators=extra_validators,
            )

        if args.check_only:
            if args.dry_run:
                raise ValueError("--check-only cannot be combined with --dry-run")
            from edison.core.qa.evidence import EvidenceService

            ev = EvidenceService(args.task_id, project_root=repo_root)
            round_num = int(args.round or ev.get_current_round() or 0)
            if not round_num:
                formatter.error("No evidence round found; run tracking/validation first", error_code="no_round")
                return 1

            bundle_data, overall_approved, cluster_missing = _compute_bundle_summary(
                args=args,
                repo_root=repo_root,
                session_id=session_id,
                validator_registry=validator_registry,
                round_num=round_num,
                extra_validators=extra_validators,
                execution_result=None,
            )
            ev.write_bundle(bundle_data, round_num=round_num)

            if formatter.json_mode:
                formatter.json_output(
                    {
                        "task_id": args.task_id,
                        "round": round_num,
                        "approved": overall_approved,
                        "missing": bundle_data.get("missing") or [],
                        "cluster_missing": cluster_missing,
                        "bundle_file": str((ev.ensure_round(round_num) / ev.bundle_filename).relative_to(repo_root)),
                    }
                )
            else:
                if overall_approved:
                    formatter.text(
                        f"All blocking validator reports approved and {ev.bundle_filename} was written."
                    )
                else:
                    formatter.text("Bundle NOT approved (missing or failing blocking reports).")
                    for tid, missing in (cluster_missing or {}).items():
                        suffix = f": {', '.join(missing)}" if missing else ""
                        formatter.text(f"  - {tid}{suffix}")

            return 0 if overall_approved else 1

        # Dry-run or roster-only mode
        results = {
            "task_id": args.task_id,
            "session_id": session_id,
            "wave": args.wave,
            "roster": roster,
            "status": "dry_run" if args.dry_run else "roster_only",
            "validators_count": len(validators_to_run),
            "execute_available": any(
                executor.can_execute_validator(v["id"]) for v in validators_to_run
            ),
        }

        if args.dry_run:
            results["execution_plan"] = []
            for v in validators_to_run:
                config = validator_registry.get(v["id"])
                can_exec = executor.can_execute_validator(v["id"])
                results["execution_plan"].append({
                    "validator_id": v["id"],
                    "engine": config.engine if config else "unknown",
                    "fallback_engine": config.fallback_engine if config else None,
                    "can_execute_directly": can_exec,
                    "would_use": "cli" if can_exec else "delegation",
                    "wave": config.wave if config else "unknown",
                })

        if formatter.json_mode:
            formatter.json_output(results)
        else:
            _display_roster(
                formatter=formatter,
                args=args,
                roster=roster,
                validators_to_run=validators_to_run,
                executor=executor,
                validator_registry=validator_registry,
            )

        return 0

    except Exception as e:
        formatter.error(e, error_code="validate_error")
        return 1


def _display_roster(
    formatter: OutputFormatter,
    args: argparse.Namespace,
    roster: dict,
    validators_to_run: list,
    executor: ValidationExecutor,
    validator_registry: ValidatorRegistry,
) -> None:
    """Display validation roster in human-readable format."""
    formatter.text(f"Validation roster for {args.task_id}:")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")

    # Show modified files
    modified_files = roster.get("modifiedFiles", [])
    if modified_files:
        formatter.text(f"  Modified files: {len(modified_files)}")
        for f in modified_files[:5]:
            formatter.text(f"    - {f}")
        if len(modified_files) > 5:
            formatter.text(f"    ... and {len(modified_files) - 5} more")
    else:
        formatter.text("  Modified files: (none detected)")

    formatter.text("")
    formatter.text(f"  Always required: {len(roster.get('alwaysRequired', []))} validators")
    formatter.text(f"  Triggered blocking: {len(roster.get('triggeredBlocking', []))} validators")
    formatter.text(f"  Triggered optional: {len(roster.get('triggeredOptional', []))} validators")

    # Show extra validators if any
    extra_added = roster.get("extraAdded", [])
    if extra_added:
        formatter.text(f"  Added by orchestrator: {len(extra_added)} validators")
    formatter.text("")

    # Group by wave for display
    waves: dict[str, list] = {}
    for v in validators_to_run:
        wave_name = v.get("wave", "unknown")
        if wave_name not in waves:
            waves[wave_name] = []
        waves[wave_name].append(v)

    for wave_name, wave_validators in waves.items():
        formatter.text(f"  Wave: {wave_name}")
        for v in wave_validators:
            can_exec = executor.can_execute_validator(v["id"])
            exec_marker = "✓" if can_exec else "→"
            blocking_marker = "⚠" if v.get("blocking") else "○"
            added_marker = "+" if v.get("addedByOrchestrator") else " "
            formatter.text(f"    {exec_marker}{added_marker}{blocking_marker} {v['id']}")
            # Show reason (trigger match or orchestrator-added)
            reason = v.get("reason", "")
            if reason:
                formatter.text(f"        {reason}")
            if args.dry_run:
                config = validator_registry.get(v["id"])
                if config:
                    engine_info = f"engine={config.engine}"
                    if not can_exec and config.fallback_engine:
                        engine_info += f" → fallback={config.fallback_engine}"
                    formatter.text(f"        ({engine_info})")
        formatter.text("")

    formatter.text("  Legend: ✓=CLI, →=delegation, ⚠=blocking, ○=optional, +=added")

    # Show skipped validators
    skipped = roster.get("skipped", [])
    if skipped:
        formatter.text("")
        formatter.text(f"  Skipped validators: {len(skipped)} (no matching files)")
        for s in skipped[:5]:
            triggers = s.get("triggers", [])
            triggers_str = ", ".join(triggers[:2])
            if len(triggers) > 2:
                triggers_str += f" +{len(triggers)-2} more"
            formatter.text(f"    - {s['id']} (triggers: {triggers_str})")

    # Show decision points (suggestions for orchestrator)
    decision_points = roster.get("decisionPoints", [])
    if decision_points:
        formatter.text("")
        formatter.text("  ═══ ORCHESTRATOR DECISION POINTS ═══")
        formatter.text("  The following validators were NOT auto-triggered but may be relevant:")
        for dp in decision_points:
            formatter.text(f"    ► {dp.get('suggestion', 'Unknown')}")
            formatter.text(f"      Reason: {dp.get('reason', 'Unknown')}")
            cmd = dp.get("command", "")
            if cmd:
                formatter.text(f"      To add: edison qa validate {args.task_id} {cmd}")
        formatter.text("")

    if not args.execute:
        formatter.text("")
        formatter.text("  To execute validators, add --execute flag")
        formatter.text("")
        formatter.text("  Orchestrator: To add extra validators:")
        formatter.text("    edison qa validate <task> --add-validators react api --execute")
        formatter.text("    edison qa validate <task> --add-validators critical:react comprehensive:api --execute")


def _compute_bundle_summary(
    *,
    args: argparse.Namespace,
    repo_root: Path,
    session_id: str | None,
    validator_registry: ValidatorRegistry,
    round_num: int,
    extra_validators: list[dict[str, str]] | None = None,
    execution_result: Any | None = None,
) -> tuple[dict[str, Any], bool, dict[str, list[str]]]:
    """Compute bundle-approved payload from existing evidence reports.

    This is the single source of truth for the bundle summary schema payload.
    """
    from edison.core.qa.bundler import build_validation_manifest
    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.time import utc_timestamp

    approved_verdicts = {"approve"}

    manifest = build_validation_manifest(
        args.task_id,
        project_root=repo_root,
        session_id=session_id,
    )
    manifest_tasks = manifest.get("tasks") or []

    tasks_payload: list[dict[str, object]] = []
    cluster_missing: dict[str, list[str]] = {}

    for t in manifest_tasks:
        task_id = str(t.get("taskId") or "")
        if not task_id:
            continue

        task_ev = EvidenceService(task_id, project_root=repo_root)
        task_round = int(task_ev.get_current_round() or 0)

        # Determine blocking validator IDs for THIS task (config-driven roster).
        #
        # IMPORTANT: approval is computed against the full blocking roster for the task.
        # CLI filters like `--validators` and `--wave` affect what we *execute* or *display*,
        # but must NOT be able to narrow the approval scope (fail-closed).
        task_roster = validator_registry.build_execution_roster(
            task_id=task_id,
            session_id=session_id,
            wave=None,
            extra_validators=extra_validators,
        )

        task_blocking_candidates = (
            (task_roster.get("alwaysRequired") or [])
            + (task_roster.get("triggeredBlocking") or [])
            + (task_roster.get("triggeredOptional") or [])
        )
        task_blocking_ids = [v.get("id") for v in task_blocking_candidates if v.get("blocking")]
        task_blocking_ids = [b for b in task_blocking_ids if isinstance(b, str) and b]

        missing_or_failed: list[str] = []
        for vid in task_blocking_ids:
            report = task_ev.read_validator_report(vid, round_num=task_round) if task_round else {}
            verdict = str((report or {}).get("verdict") or "").strip().lower()
            if verdict not in approved_verdicts:
                missing_or_failed.append(vid)

        task_approved = (not missing_or_failed) and bool(task_blocking_ids) and bool(task_round)
        if not task_approved:
            cluster_missing[task_id] = missing_or_failed

        tasks_payload.append(
            {
                **t,
                "approved": task_approved,
                "evidenceRound": task_round,
                "blockingMissingOrFailed": missing_or_failed,
            }
        )

    overall_approved = bool(tasks_payload) and all(bool(t.get("approved")) for t in tasks_payload)
    missing_flat = sorted({vid for vids in cluster_missing.values() for vid in (vids or []) if vid})

    validators_payload: list[dict[str, object]] = []
    if execution_result is not None:
        try:
            validators_payload = [
                {"validatorId": v.validator_id, "verdict": v.verdict}
                for w in execution_result.waves
                for v in w.validators
            ]
        except Exception:
            validators_payload = []

    bundle_data: dict[str, Any] = {
        "taskId": args.task_id,
        "rootTask": args.task_id,
        "round": int(round_num),
        "approved": overall_approved,
        "generatedAt": utc_timestamp(),
        "tasks": tasks_payload,
        "validators": validators_payload,
        "missing": missing_flat,
        "nonBlockingFollowUps": [],
    }

    return bundle_data, overall_approved, cluster_missing


def _execute_with_executor(
    args: argparse.Namespace,
    repo_root: Path,
    executor: ValidationExecutor,
    formatter: OutputFormatter,
    session_id: str | None,
    extra_validators: list[dict[str, str]] | None = None,
) -> int:
    """Execute validators using the centralized executor."""
    # Resolve worktree path: prefer explicit override, fallback to repo_root
    worktree_path = Path(args.worktree_path) if getattr(args, "worktree_path", None) else repo_root

    formatter.text(f"Executing validators for {args.task_id}...")
    formatter.text(f"  Worktree: {worktree_path}")
    formatter.text(f"  Mode: {'sequential' if args.sequential else f'parallel (max {args.max_workers} workers)'}")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")
    if extra_validators:
        formatter.text(f"  Extra validators: {', '.join(e['id'] for e in extra_validators)}")

    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence import rounds as evidence_rounds

    ev = EvidenceService(args.task_id, project_root=repo_root)

    # Resolve the evidence round deterministically (and print it) so operators know where artifacts go.
    round_num: int
    if getattr(args, "new_round", False):
        created = ev.create_next_round()
        round_num = evidence_rounds.get_round_number(created)
    elif args.round is not None:
        round_num = int(args.round)
        ev.ensure_round(round_num)
    else:
        current = ev.get_current_round()
        if current is None:
            created = ev.create_next_round()
            round_num = evidence_rounds.get_round_number(created)
        else:
            round_num = int(current)

    try:
        from edison.core.utils.paths import PathResolver

        project_root = PathResolver.resolve_project_root()
        round_dir = ev.get_round_dir(round_num)
        try:
            display_round = str(round_dir.relative_to(project_root))
        except Exception:
            display_round = str(round_dir)
    except Exception:
        display_round = f"<evidence-root>/{args.task_id}/round-{round_num}"

    formatter.text(f"  Round: {round_num}")
    formatter.text(f"  Evidence: {display_round}")
    formatter.text("")

    # Execute using centralized executor
    result = executor.execute(
        task_id=args.task_id,
        session_id=session_id or "cli",
        worktree_path=worktree_path,
        wave=args.wave,
        validators=args.validators,
        blocking_only=args.blocking_only,
        parallel=not args.sequential,
        round_num=round_num,
        evidence_service=ev,
        timeout=getattr(args, "timeout", None),
        timeout_multiplier=getattr(args, "timeout_multiplier", None),
    )

    # ---------------------------------------------------------------------
    # Fail-closed bundle approval:
    #
    # - `ExecutionResult.all_blocking_passed` is intentionally permissive and
    #   treats delegated validators as "pending" (not failed) so execution can
    #   proceed across waves.
    # - For promotion guards (qa wip→done, task done→validated) we must require
    #   explicit approvals for ALL blocking validators.
    # - Therefore: determine blocking validator IDs from the registry roster and
    #   verify per-validator reports in evidence are approved.
    # ---------------------------------------------------------------------
    round_num = int(result.round_num or round_num or 0)

    validator_registry = executor.get_validator_registry()

    bundle_data, overall_approved, cluster_missing = _compute_bundle_summary(
        args=args,
        repo_root=repo_root,
        session_id=session_id,
        validator_registry=validator_registry,
        round_num=round_num,
        extra_validators=extra_validators,
        execution_result=result,
    )

    # Always emit/refresh the bundle summary for the root task when we have a round.
    if round_num:
        ev.write_bundle(bundle_data, round_num=round_num)

    # Display wave-by-wave results
    for wave_result in result.waves:
        formatter.text(f"  Wave: {wave_result.wave}")

        for v in wave_result.validators:
            passed = v.verdict == "approve"
            status_icon = "✓" if passed else "✗" if v.verdict in ("reject", "blocked", "error") else "?"
            duration_str = f" ({v.duration:.1f}s)" if v.duration else ""
            formatter.text(f"    {status_icon} {v.validator_id}: {v.verdict}{duration_str}")

        if wave_result.delegated:
            formatter.text(f"    → Delegated: {', '.join(wave_result.delegated)}")

        if wave_result.blocking_failed:
            formatter.text(f"    ✗ Blocking failures: {', '.join(wave_result.blocking_failed)}")

        formatter.text("")

    # Summary
    formatter.text(
        f"Results: {result.passed_count} passed, {result.failed_count} failed, "
        f"{result.pending_count} pending"
    )

    # Show delegated validators requiring orchestrator action
    if result.delegated_validators:
        formatter.text("")
        formatter.text("═══ ORCHESTRATOR ACTION REQUIRED ═══")
        formatter.text("The following validators could not execute directly:")
        for validator_id in result.delegated_validators:
            try:
                details = executor.can_execute_validator_details(validator_id)
            except Exception:
                details = {"validatorId": validator_id, "canExecute": False, "reason": "unknown"}

            reason = str(details.get("reason") or "unknown")
            detail = str(details.get("detail") or "").strip()
            command = details.get("command")

            hint = ""
            if reason == "disabled_by_config":
                hint = "disabled by config (set orchestration.allowCliEngines=true)"
            elif reason == "binary_missing":
                hint = f"command missing: {command}" if command else "command missing"
            elif reason == "config_error":
                hint = "config error"
            elif reason == "no_command":
                hint = "engine missing command"
            elif reason == "unknown_validator":
                hint = "unknown validator"
            else:
                hint = reason

            formatter.text(f"  → {validator_id}: {hint}")
            if detail:
                formatter.text(f"    {detail}")
        formatter.text("")
        formatter.text("Delegation instructions saved to evidence folder.")
        formatter.text("The orchestrator/LLM must:")
        try:
            from edison.core.utils.paths import PathResolver

            project_root = PathResolver.resolve_project_root()
            delegation_glob = ev.get_round_dir(round_num) / "delegation-*.md"
            try:
                display = str(delegation_glob.relative_to(project_root))
            except Exception:
                display = str(delegation_glob)
        except Exception:
            display = "<evidence-root>/<task-id>/round-N/delegation-*.md"

        formatter.text(f"  1. Read delegation instructions from: {display}")
        formatter.text("  2. Execute validation manually using the specified palRole")
        formatter.text("  3. Save results to: validator-<id>-report.md")
        formatter.text("")
        formatter.text("After completing delegated validations:")
        formatter.text(f"  edison qa validate {args.task_id} --execute  # Re-run to check status")

    if result.blocking_failed:
        formatter.text("")
        formatter.text(f"Blocking failures: {', '.join(result.blocking_failed)}")
        formatter.text("")
        formatter.text("Next steps:")
        formatter.text(f"  edison qa round {args.task_id} --status reject  # Record outcome in QA history")
        formatter.text(f"  edison qa validate {args.task_id} --execute --new-round  # Re-run in fresh evidence round")
    elif overall_approved:
        formatter.text("")
        formatter.text(f"All blocking validators approved and {ev.bundle_filename} was written. Next steps:")
        formatter.text(f"  edison qa promote {args.task_id} --status done")
    elif result.delegated_validators or cluster_missing:
        formatter.text("")
        formatter.text("Awaiting cluster approvals (some validators may be delegated).")
        if cluster_missing:
            for tid, missing in cluster_missing.items():
                suffix = f": {', '.join(missing)}" if missing else ""
                formatter.text(f"  - {tid}{suffix}")

    # JSON output if requested
    if formatter.json_mode:
        json_data = result.to_dict()
        json_data["worktree_path"] = str(worktree_path)
        json_data["evidence_path"] = display_round
        formatter.json_output(json_data)

    return 0 if overall_approved else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed_args = parser.parse_args()
    sys.exit(main(parsed_args))
