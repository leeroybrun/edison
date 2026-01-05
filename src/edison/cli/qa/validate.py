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
        "--scope",
        choices=["auto", "hierarchy", "bundle"],
        help="Validation bundle scope (default: config or auto)",
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
        help="Specific wave to validate (e.g., global, critical, comprehensive)",
    )
    parser.add_argument(
        "--preset",
        type=str,
        help="Validation preset override (e.g., fast, standard, strict, deep)",
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
        default=None,
        help="Maximum parallel workers (default: from config)",
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

        # Resolve max workers from config when not explicitly provided.
        max_workers = getattr(args, "max_workers", None)
        if max_workers is None:
            try:
                from edison.core.config.domains.qa import QAConfig

                max_workers = QAConfig(repo_root=repo_root).get_max_concurrent_validators()
            except Exception:
                max_workers = 4

        # Create executor (centralized in core)
        executor = ValidationExecutor(
            project_root=repo_root,
            max_workers=int(max_workers),
        )
        # Use ValidatorRegistry (single source of truth) for roster building
        validator_registry = executor.get_validator_registry()

        # Build extra validators list from --add-validators using unified syntax
        extra_validators = None
        if getattr(args, "add_validators", None):
            extra_validators = validator_registry.parse_extra_validators(args.add_validators)

        # Resolve the validation cluster (scope + root) deterministically.
        from edison.core.qa.bundler import build_validation_manifest

        manifest = build_validation_manifest(
            args.task_id,
            scope=getattr(args, "scope", None),
            project_root=repo_root,
            session_id=session_id,
        )
        root_task_id = str(manifest.get("rootTask") or args.task_id)
        scope_used = str(manifest.get("scope") or "hierarchy")
        manifest_tasks = list(manifest.get("tasks") or [])
        cluster_task_ids = [str(t.get("taskId") or "") for t in manifest_tasks if isinstance(t, dict) and t.get("taskId")]

        # Resolve preset name deterministically.
        #
        # In the Edison repo, `validation.sessionClose.preset` is a stricter "deep" preset
        # that we want by default when actually executing validators. Roster-only and
        # check-only flows should remain fast by default.
        preset_name = getattr(args, "preset", None)
        if args.execute and not preset_name:
            try:
                from edison.core.config.domains.qa import QAConfig

                session_close = QAConfig(repo_root=repo_root).validation_config.get("sessionClose", {}) or {}
                if isinstance(session_close, dict):
                    candidate = str(session_close.get("preset") or "").strip()
                    if candidate:
                        preset_name = candidate
            except Exception:
                preset_name = preset_name

        # Build validator roster for display
        roster = validator_registry.build_execution_roster(
            task_id=args.task_id,
            session_id=session_id,
            wave=args.wave,
            extra_validators=extra_validators,
            preset_name=preset_name,
        )
        preset_used = str(roster.get("preset") or preset_name or "").strip()

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

        # QA validate preflight checklist (surface prerequisites early).
        from edison.core.workflow.checklists.qa_validate_preflight import (
            QAValidatePreflightChecklistEngine,
        )

        will_execute = bool(args.execute and not args.dry_run and not args.check_only)
        preflight_checklist = QAValidatePreflightChecklistEngine(project_root=repo_root).compute(
            task_id=str(args.task_id),
            session_id=session_id,
            roster=roster,
            round_num=int(args.round) if args.round is not None else None,
            new_round=bool(getattr(args, "new_round", False)),
            will_execute=will_execute,
            check_only=bool(getattr(args, "check_only", False)),
            root_task_id=root_task_id,
            scope_used=scope_used,
            cluster_task_ids=cluster_task_ids,
        )

        # Execute mode: use centralized executor
        if args.execute and not args.dry_run:
            validators_override: list[str] | None = None
            if not getattr(args, "validators", None) and len(cluster_task_ids) > 1:
                # Union the execution roster across the cluster so we run validators once at the
                # bundle root, but still cover all tasks in the cluster.
                union_ids: set[str] = set()
                for tid in cluster_task_ids:
                    r = validator_registry.build_execution_roster(
                        task_id=str(tid),
                        session_id=session_id,
                        wave=args.wave,
                        extra_validators=extra_validators,
                        preset_name=preset_name,
                    )
                    candidates = (r.get("alwaysRequired", []) or []) + (r.get("triggeredBlocking", []) or [])
                    if not bool(getattr(args, "blocking_only", False)):
                        candidates = candidates + (r.get("triggeredOptional", []) or [])
                    for v in candidates:
                        if not isinstance(v, dict) or not v.get("id"):
                            continue
                        union_ids.add(str(v.get("id")))
                validators_override = sorted({vid for vid in union_ids if vid})

            return _execute_with_executor(
                args=args,
                repo_root=repo_root,
                executor=executor,
                formatter=formatter,
                session_id=session_id,
                extra_validators=extra_validators,
                checklist=preflight_checklist,
                root_task_id=root_task_id,
                scope_used=scope_used,
                cluster_task_ids=cluster_task_ids,
                manifest_tasks=manifest_tasks,
                preset_used=preset_used,
                validators_override=validators_override,
            )

        if args.check_only:
            if args.dry_run:
                raise ValueError("--check-only cannot be combined with --dry-run")

            if not formatter.json_mode:
                _display_preflight_checklist(formatter=formatter, checklist=preflight_checklist)
            from edison.core.qa.evidence import EvidenceService

            root_ev = EvidenceService(root_task_id, project_root=repo_root)
            round_num = int(args.round or root_ev.get_current_round() or 0)
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
                root_task_id=root_task_id,
                scope_used=scope_used,
                cluster_task_ids=cluster_task_ids,
                manifest_tasks=manifest_tasks,
                preset_used=str(roster.get("preset") or getattr(args, "preset", "") or "").strip(),
            )

            # Write bundle summary at root and mirror into each member evidence dir.
            root_ev.write_bundle(bundle_data, round_num=round_num)

            if formatter.json_mode:
                formatter.json_output(
                    {
                        "task_id": args.task_id,
                        "round": round_num,
                        "preset": str(roster.get("preset") or getattr(args, "preset", "") or "").strip(),
                        "approved": overall_approved,
                        "missing": bundle_data.get("missing") or [],
                        "cluster_missing": cluster_missing,
                        "checklist": preflight_checklist,
                        "bundle_file": str(
                            (root_ev.ensure_round(round_num) / root_ev.bundle_filename).relative_to(repo_root)
                        ),
                    }
                )
            else:
                if overall_approved:
                    formatter.text(
                        f"All blocking validator reports approved and {root_ev.bundle_filename} was written."
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
            "checklist": preflight_checklist,
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
            _display_preflight_checklist(formatter=formatter, checklist=preflight_checklist)
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
    root_task_id: str,
    scope_used: str,
    cluster_task_ids: list[str],
    manifest_tasks: list[dict[str, Any]],
    preset_used: str = "",
) -> tuple[dict[str, Any], bool, dict[str, list[str]]]:
    """Compute bundle-approved payload from existing evidence reports.

    This is the single source of truth for the bundle summary schema payload.
    """
    from edison.core.qa.evidence import EvidenceService
    from edison.core.utils.time import utc_timestamp

    approved_verdicts = {"approve"}

    # Determine the union of blocking validator IDs across all tasks in the cluster.
    # Approval is computed against the preset-selected blocking set (when provided),
    # plus any always-required/triggered blocking validators.
    blocking_ids: set[str] = set()
    for tid in cluster_task_ids:
        preset_name = str(preset_used or "").strip() or None

        # Fail-closed: if a preset declares blocking validators, they are always required for approval,
        # even if the validator registry cannot resolve them (missing config should block promotion).
        try:
            from edison.core.qa.policy.resolver import ValidationPolicyResolver

            policy = ValidationPolicyResolver(project_root=repo_root).resolve_for_task(
                str(tid),
                session_id=session_id,
                preset_name=preset_name,
            )
            for vid in policy.blocking_validators:
                if str(vid).strip():
                    blocking_ids.add(str(vid).strip())
        except Exception:
            pass

        task_roster = validator_registry.build_execution_roster(
            task_id=str(tid),
            session_id=session_id,
            wave=None,
            extra_validators=extra_validators,
            preset_name=preset_name,
        )
        candidates = (
            (task_roster.get("alwaysRequired") or [])
            + (task_roster.get("triggeredBlocking") or [])
            + (task_roster.get("triggeredOptional") or [])
            + (task_roster.get("extraAdded") or [])
        )
        for v in candidates:
            if not isinstance(v, dict) or not v.get("blocking"):
                continue
            vid = str(v.get("id") or "").strip()
            if vid:
                blocking_ids.add(vid)

    root_ev = EvidenceService(str(root_task_id), project_root=repo_root)

    # Fail-closed: if a blocking validator report exists in the round evidence dir,
    # it must be included in approval even if it was not part of the preset roster.
    # This prevents ignoring a known blocking signal (e.g. security reject) during check-only.
    try:
        for report_path in root_ev.list_validator_reports(round_num=int(round_num)):
            name = report_path.name
            if not (name.startswith("validator-") and name.endswith("-report.md")):
                continue
            vid = name[len("validator-") : -len("-report.md")].strip()
            if not vid:
                continue
            cfg = validator_registry.get(vid)
            if cfg is not None and bool(getattr(cfg, "blocking", False)):
                blocking_ids.add(vid)
    except Exception:
        pass

    missing_or_failed: list[str] = []
    verdicts: dict[str, str] = {}
    for vid in sorted(blocking_ids):
        report = root_ev.read_validator_report(vid, round_num=int(round_num)) or {}
        verdict = str((report or {}).get("verdict") or "").strip().lower()
        verdicts[vid] = verdict
        if verdict not in approved_verdicts:
            missing_or_failed.append(vid)

    overall_approved = not missing_or_failed

    tasks_payload: list[dict[str, Any]] = []
    for t in manifest_tasks:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("taskId") or "").strip()
        if tid and tid in set(cluster_task_ids):
            tasks_payload.append({**t, "approved": overall_approved})

    cluster_missing: dict[str, list[str]] = {}
    if not overall_approved:
        for tid in cluster_task_ids:
            cluster_missing[str(tid)] = list(missing_or_failed)

    validators_payload: list[dict[str, Any]] = []
    if execution_result is not None:
        try:
            validators_payload = [
                {"validatorId": v.validator_id, "verdict": v.verdict}
                for w in execution_result.waves
                for v in w.validators
            ]
        except Exception:
            validators_payload = []
    if not validators_payload:
        validators_payload = [{"validatorId": vid, "verdict": verdicts.get(vid)} for vid in sorted(blocking_ids)]

    bundle_data: dict[str, Any] = {
        "taskId": str(root_task_id),
        "rootTask": str(root_task_id),
        "scope": str(scope_used),
        "preset": str(preset_used or "").strip() or None,
        "round": int(round_num),
        "approved": bool(overall_approved),
        "generatedAt": utc_timestamp(),
        "tasks": tasks_payload,
        "validators": validators_payload,
        "missing": sorted({str(v) for v in missing_or_failed if v}),
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
    checklist: dict[str, Any] | None = None,
    *,
    root_task_id: str,
    scope_used: str,
    cluster_task_ids: list[str],
    manifest_tasks: list[dict[str, Any]],
    preset_used: str,
    validators_override: list[str] | None = None,
) -> int:
    """Execute validators using the centralized executor."""
    if checklist is not None:
        _display_preflight_checklist(formatter=formatter, checklist=checklist)

    formatter.text(f"Executing validators for {root_task_id}...")
    formatter.text(f"  Mode: {'sequential' if args.sequential else f'parallel (max {args.max_workers} workers)'}")
    if args.wave:
        formatter.text(f"  Wave: {args.wave}")
    if extra_validators:
        formatter.text(f"  Extra validators: {', '.join(e['id'] for e in extra_validators)}")

    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence import rounds as evidence_rounds

    ev = EvidenceService(root_task_id, project_root=repo_root)

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
        display_round = f"<evidence-root>/{root_task_id}/round-{round_num}"

    formatter.text(f"  Round: {round_num}")
    formatter.text(f"  Evidence: {display_round}")
    formatter.text("")

    # Ensure round artifacts exist BEFORE executing any validator.
    #
    # Validators read the bundle summary + implementation report paths from the
    # generated prompt prelude. If we only write these artifacts after execution,
    # CLI validators can (correctly) reject due to missing context.
    try:
        ev.ensure_round(round_num)

        existing_impl: dict[str, Any] = {}
        try:
            existing_impl = ev.read_implementation_report(round_num)
        except Exception:
            existing_impl = {}

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

        from edison.core.utils.time import utc_timestamp

        draft_bundle = {
            "taskId": root_task_id,
            "rootTask": root_task_id,
            "scope": scope_used,
            "preset": str(preset_used or "").strip() or None,
            "round": int(round_num),
            "approved": False,
            "generatedAt": utc_timestamp(),
            "tasks": [{**t, "approved": False} for t in (manifest_tasks or [])],
            "validators": [],
            "nonBlockingFollowUps": [],
        }
        ev.write_bundle(draft_bundle, round_num=round_num)
    except Exception:
        # Fail-open: validation execution should still proceed even if
        # artifact initialization fails (executor will write bundle summary later).
        pass

    # Execute using centralized executor
    result = executor.execute(
        task_id=root_task_id,
        session_id=session_id or "cli",
        worktree_path=repo_root,
        wave=args.wave,
        validators=validators_override if validators_override is not None else args.validators,
        blocking_only=args.blocking_only,
        parallel=not args.sequential,
        round_num=round_num,
        evidence_service=ev,
        extra_validators=extra_validators,
        preset_name=str(getattr(args, "preset", None) or "").strip() or None,
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
        root_task_id=root_task_id,
        scope_used=scope_used,
        cluster_task_ids=cluster_task_ids,
        manifest_tasks=manifest_tasks,
        preset_used=str(preset_used or "").strip(),
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
                hint = "disabled by config (set orchestration.allowCliEngines=true in .edison/config/orchestration.yaml)"
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
        formatter.json_output(result.to_dict())

    return 0 if overall_approved else 1


def _display_preflight_checklist(*, formatter: OutputFormatter, checklist: dict[str, Any]) -> None:
    items = checklist.get("items") if isinstance(checklist, dict) else None
    if not isinstance(items, list) or not items:
        return

    has_blockers = bool(checklist.get("hasBlockers", False))
    header = "QA validate preflight checklist:"
    if has_blockers:
        header += " (BLOCKERS present)"
    formatter.text(header)

    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Unknown")
        severity = str(item.get("severity") or "info")
        status = str(item.get("status") or "unknown")
        tag = "OK"
        if status != "ok":
            tag = "BLOCK" if severity == "blocker" else ("WARN" if severity == "warning" else "INFO")
        formatter.text(f"  - [{tag}] {title}")
        rationale = str(item.get("rationale") or "").strip()
        if rationale:
            formatter.text(f"      {rationale}")
        cmds = item.get("suggestedCommands") or []
        if status != "ok" and isinstance(cmds, list) and cmds:
            for cmd in cmds[:3]:
                formatter.text(f"      -> {cmd}")

    formatter.text("")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed_args = parser.parse_args()
    sys.exit(main(parsed_args))
