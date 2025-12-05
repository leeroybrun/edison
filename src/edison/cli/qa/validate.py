"""
Edison qa validate command.

SUMMARY: Run validators against a task bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.qa.engines import EngineRegistry, ValidationExecutor

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
        registry = executor.get_registry()

        # Build validator roster for display
        roster = registry.build_execution_roster(
            task_id=args.task_id,
            session_id=args.session,
            wave=args.wave,
        )

        if args.blocking_only:
            roster["triggeredOptional"] = []

        # Filter to specific validators if requested
        if args.validators:
            roster = {
                "taskId": roster.get("taskId"),
                "alwaysRequired": [
                    v for v in roster.get("alwaysRequired", []) if v["id"] in args.validators
                ],
                "triggeredBlocking": [
                    v for v in roster.get("triggeredBlocking", []) if v["id"] in args.validators
                ],
                "triggeredOptional": [
                    v for v in roster.get("triggeredOptional", []) if v["id"] in args.validators
                ],
                "totalBlocking": 0,
                "decisionPoints": [],
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
                config = registry.get_validator(v["id"])
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
                registry=registry,
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
    registry: EngineRegistry,
) -> None:
    """Display validation roster in human-readable format."""
    formatter.text(f"Validation roster for {args.task_id}:")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")
    formatter.text(f"  Always required: {len(roster.get('alwaysRequired', []))} validators")
    formatter.text(f"  Triggered blocking: {len(roster.get('triggeredBlocking', []))} validators")
    formatter.text(f"  Triggered optional: {len(roster.get('triggeredOptional', []))} validators")
    formatter.text("")

    # Group by wave for display
    waves: dict[str, list] = {}
    for v in validators_to_run:
        config = registry.get_validator(v["id"])
        wave_name = config.wave if config else "unknown"
        if wave_name not in waves:
            waves[wave_name] = []
        waves[wave_name].append((v, config))

    for wave_name, wave_validators in waves.items():
        formatter.text(f"  Wave: {wave_name}")
        for v, config in wave_validators:
            can_exec = executor.can_execute_validator(v["id"])
            exec_marker = "✓" if can_exec else "→"
            blocking_marker = "⚠" if v.get("blocking") else "○"
            formatter.text(f"    {exec_marker} {blocking_marker} {v['id']}")
            if args.dry_run and config:
                engine_info = f"engine={config.engine}"
                if not can_exec and config.fallback_engine:
                    engine_info += f" → fallback={config.fallback_engine}"
                formatter.text(f"        ({engine_info})")
        formatter.text("")

    formatter.text("  Legend: ✓=CLI available, →=delegation, ⚠=blocking, ○=optional")

    if not args.execute:
        formatter.text("")
        formatter.text("  To execute validators, add --execute flag")


def _execute_with_executor(
    args: argparse.Namespace,
    repo_root: Path,
    executor: ValidationExecutor,
    formatter: OutputFormatter,
) -> int:
    """Execute validators using the centralized executor."""
    formatter.text(f"Executing validators for {args.task_id}...")
    formatter.text(f"  Mode: {'sequential' if args.sequential else f'parallel (max {args.max_workers} workers)'}")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")
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
        formatter.text("  1. Read delegation instructions from: .project/qa/evidence/<task>/round-N/delegation-*.md")
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
        formatter.text(f"  edison qa round --task {args.task_id} --status rejected")
    elif result.all_blocking_passed and result.failed_count == 0 and not result.delegated_validators:
        formatter.text("")
        formatter.text("All validators passed! Next steps:")
        formatter.text(f"  edison qa promote --task {args.task_id} --to done")
    elif result.all_blocking_passed and result.delegated_validators:
        formatter.text("")
        formatter.text("CLI validators passed. Awaiting delegated validator results.")

    # JSON output if requested
    if formatter.json_mode:
        formatter.json_output(result.to_dict())

    return 0 if result.all_blocking_passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed_args = parser.parse_args()
    sys.exit(main(parsed_args))
