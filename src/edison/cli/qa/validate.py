"""
Edison qa validate command.

SUMMARY: Run validators against a task bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
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
        help="Validation round number (default: create new round)",
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
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Run validators - delegates to core ValidationExecutor."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

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
            session_id=args.session,
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
                extra_validators=extra_validators,
            )

        # Dry-run or roster-only mode
        results = {
            "task_id": args.task_id,
            "session_id": args.session,
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


def _execute_with_executor(
    args: argparse.Namespace,
    repo_root: Path,
    executor: ValidationExecutor,
    formatter: OutputFormatter,
    extra_validators: list[dict[str, str]] | None = None,
) -> int:
    """Execute validators using the centralized executor."""
    formatter.text(f"Executing validators for {args.task_id}...")
    formatter.text(f"  Mode: {'sequential' if args.sequential else f'parallel (max {args.max_workers} workers)'}")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")
    if extra_validators:
        formatter.text(f"  Extra validators: {', '.join(e['id'] for e in extra_validators)}")
    formatter.text("")

    # Execute using centralized executor
    result = executor.execute(
        task_id=args.task_id,
        session_id=args.session or "cli",
        worktree_path=repo_root,
        wave=args.wave,
        validators=args.validators,
        blocking_only=args.blocking_only,
        parallel=not args.sequential,
        round_num=args.round,
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
    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.time import utc_timestamp

    ev = EvidenceService(args.task_id, project_root=repo_root)
    round_num = int(result.round_num or 0)

    validator_registry = executor.get_validator_registry()
    roster = validator_registry.build_execution_roster(
        task_id=args.task_id,
        session_id=args.session,
        wave=args.wave,
        extra_validators=extra_validators,
    )

    # Apply same CLI filtering semantics as roster display.
    if args.blocking_only:
        roster["triggeredOptional"] = []

    if getattr(args, "validators", None):
        wanted = set(args.validators or [])
        for k in ("alwaysRequired", "triggeredBlocking", "triggeredOptional"):
            roster[k] = [v for v in roster.get(k, []) if v.get("id") in wanted]

    blocking_candidates = (
        (roster.get("alwaysRequired") or [])
        + (roster.get("triggeredBlocking") or [])
        + (roster.get("triggeredOptional") or [])
    )
    blocking_ids = [v.get("id") for v in blocking_candidates if v.get("blocking")]
    blocking_ids = [b for b in blocking_ids if isinstance(b, str) and b]

    approved_verdicts = {"approve", "approved", "pass", "passed"}
    blocking_missing_or_failed: list[str] = []
    for vid in blocking_ids:
        report = ev.read_validator_report(vid, round_num=round_num) if round_num else {}
        verdict = str((report or {}).get("verdict") or "").strip().lower()
        if verdict not in approved_verdicts:
            blocking_missing_or_failed.append(vid)

    all_blocking_approved = (not blocking_missing_or_failed) and bool(blocking_ids)

    # If all blocking validators approved, emit/refresh bundle-approved.json.
    if all_blocking_approved and round_num:
        bundle_data = {
            "taskId": args.task_id,
            "round": round_num,
            "approved": True,
            "generatedAt": utc_timestamp(),
            # Single-task fallback: embed a per-task approval list for future cluster support.
            "tasks": [{"taskId": args.task_id, "approved": True}],
            "validators": [
                {
                    "validatorId": v.validator_id,
                    "verdict": v.verdict,
                }
                for w in result.waves
                for v in w.validators
            ],
            "nonBlockingFollowUps": [],
        }
        ev.write_bundle(bundle_data, round_num=round_num)

    # Display wave-by-wave results
    for wave_result in result.waves:
        formatter.text(f"  Wave: {wave_result.wave}")

        for v in wave_result.validators:
            passed = v.verdict in ("approve", "approved", "pass", "passed")
            status_icon = "✓" if passed else "✗" if v.verdict in ("reject", "rejected", "error") else "?"
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
        formatter.text("The following validators could not execute directly (CLI not available):")
        for validator_id in result.delegated_validators:
            formatter.text(f"  → {validator_id}")
        formatter.text("")
        formatter.text("Delegation instructions saved to evidence folder.")
        formatter.text("The orchestrator/LLM must:")
        formatter.text("  1. Read delegation instructions from: .project/qa/validation-evidence/<task>/round-N/delegation-*.md")
        formatter.text("  2. Execute validation manually using the specified zenRole")
        formatter.text("  3. Save results to: validator-<id>-report.json")
        formatter.text("")
        formatter.text("After completing delegated validations:")
        formatter.text(f"  edison qa validate {args.task_id} --execute  # Re-run to check status")

    if result.blocking_failed:
        formatter.text("")
        formatter.text(f"Blocking failures: {', '.join(result.blocking_failed)}")
        formatter.text("")
        formatter.text("Next steps:")
        formatter.text(f"  edison qa round {args.task_id} --status rejected")
    elif all_blocking_approved:
        formatter.text("")
        formatter.text("All blocking validators approved and bundle-approved.json was written. Next steps:")
        formatter.text(f"  edison qa promote {args.task_id} --status done")
    elif result.delegated_validators or blocking_missing_or_failed:
        formatter.text("")
        formatter.text("Awaiting blocking validator approvals (some may be delegated).")
        if blocking_missing_or_failed:
            formatter.text(f"Missing/insufficient blocking reports: {', '.join(blocking_missing_or_failed)}")

    # JSON output if requested
    if formatter.json_mode:
        formatter.json_output(result.to_dict())

    return 0 if all_blocking_approved else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed_args = parser.parse_args()
    sys.exit(main(parsed_args))
