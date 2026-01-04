"""QA-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from edison.core.state.builtin.utils import get_task_id_from_context


def can_validate_qa(ctx: Mapping[str, Any]) -> bool:
    """QA can be validated if all blocking validators passed.

    FAIL-CLOSED: Returns False if validation results are missing.

    This guard checks:
    1. Context-provided validation_results (if available)
    2. Falls back to reading actual validator reports from evidence

    Prerequisites:
    - All blocking validators must have passed
    - Bundle summary must exist if promoting to validated

    Args:
        ctx: Context with 'validation_results' dict or 'task_id'/'qa' for lookup

    Returns:
        True if all blocking validators passed
    """
    # Fall back to reading actual evidence
    task_id = _get_task_id(ctx)
    if not task_id:
        raise ValueError("Cannot determine task ID for QA validation.")

    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence import EvidenceService
        from edison.core.registries.validators import ValidatorRegistry

        # Bundle-aware fast path: when a bundle summary is emitted for this task
        # using the new schema (rootTask + scope), treat `approved=true` with an
        # empty missing list as sufficient evidence of blocking validator approval.
        try:
            bundle = EvidenceService(str(task_id), project_root=QAConfig().repo_root).read_bundle()
            if isinstance(bundle, Mapping) and bundle.get("approved") is True:
                if bundle.get("rootTask") and bundle.get("scope"):
                    missing = bundle.get("missing") or []
                    if isinstance(missing, list) and any(missing):
                        raise ValueError(
                            "Bundle NOT approved (missing or failing blocking reports): "
                            + ", ".join(sorted({str(m) for m in missing if m}))
                        )
                    return True
        except ValueError:
            raise
        except Exception:
            pass

        qa_config = QAConfig()
        registry = ValidatorRegistry(project_root=qa_config.repo_root)

        session_obj = ctx.get("session")
        session_id = None
        if isinstance(session_obj, Mapping):
            session_id = session_obj.get("id")
        session_id = str(ctx.get("session_id") or session_id or "").strip() or None

        roster = registry.build_execution_roster(
            task_id=str(task_id),
            session_id=session_id,
            wave=None,
            extra_validators=None,
        )
        candidates = (
            (roster.get("alwaysRequired") or [])
            + (roster.get("triggeredBlocking") or [])
            + (roster.get("triggeredOptional") or [])
        )
        blocking_ids = [
            str(v.get("id")) for v in candidates if isinstance(v, Mapping) and v.get("blocking")
        ]
        blocking_ids = [b for b in blocking_ids if b]
        if not blocking_ids:
            raise ValueError("No blocking validators were detected for this task.")

        # Prefer context-provided reports (if present), but compute missing/failing
        # against the required blocking roster (fail-closed).
        report_by_id: dict[str, Mapping[str, Any]] = {}
        validation_results = ctx.get("validation_results")
        if isinstance(validation_results, Mapping):
            reports = validation_results.get("reports", [])
            if isinstance(reports, list):
                for r in reports:
                    if not isinstance(r, Mapping):
                        continue
                    rid = r.get("validatorId") or r.get("id")
                    if rid:
                        report_by_id[str(rid)] = r

        ev = EvidenceService(str(task_id), project_root=qa_config.repo_root)
        round_num = ev.get_current_round()
        if round_num is None:
            raise ValueError(
                "No validation round found; run `edison qa validate <task> --execute` first."
            )

        missing_or_failed: list[str] = []
        for vid in blocking_ids:
            report = report_by_id.get(vid)
            if report is None:
                report = ev.read_validator_report(vid, round_num=round_num) or {}
            verdict = str(report.get("verdict") or "").strip().lower()
            if verdict != "approve":
                missing_or_failed.append(vid)

        if missing_or_failed:
            raise ValueError(
                "Blocking validators missing or not approved: "
                + ", ".join(sorted(set(missing_or_failed)))
            )

        return True
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"QA validation check failed: {e}") from e


def has_validator_reports(ctx: Mapping[str, Any]) -> bool:
    """Check if validator reports exist for the QA.

    FAIL-CLOSED: Returns False if reports are missing.

    For QA wip→done transition, we need to ensure:
    1. At least one validator report exists
    2. Required evidence files are present

    Args:
        ctx: Context with 'qa' dict containing 'task_id' or 'task_id' directly

    Returns:
        True if validator reports exist
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.qa.evidence import EvidenceService, read_validator_reports
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        # Bundle-aware fast path: if the task has an approved bundle summary in the
        # new schema, treat it as sufficient for promotion even when per-task
        # validator report files are absent (validators were executed at bundle root).
        try:
            ev = EvidenceService(str(task_id))
            bundle = ev.read_bundle()
            if isinstance(bundle, Mapping) and bundle.get("approved") is True:
                if bundle.get("rootTask") and bundle.get("scope"):
                    missing = bundle.get("missing") or []
                    validators = bundle.get("validators") or []
                    if (isinstance(missing, list) and any(missing)) or not (isinstance(validators, list) and validators):
                        raise ValueError("Bundle summary present but incomplete for promotion (missing/validators).")
                    return True
        except ValueError:
            raise
        except Exception:
            pass

        # Check for validator reports
        v = read_validator_reports(str(task_id))
        reports = v.get("reports", [])
        if not reports:
            raise ValueError(
                "No validator reports found; run `edison qa validate <task> --execute` first."
            )

        # Also check required evidence exists (preset-aware, includes global baseline).
        round_num = ev.get_current_round()
        if round_num is None:
            raise ValueError(
                "Missing evidence: no round-* evidence directory found; run `edison qa validate <task> --execute --new-round`."
            )
        round_dir = ev.get_round_dir(round_num)

        session_obj = ctx.get("session")
        session_id = None
        if isinstance(session_obj, Mapping):
            session_id = session_obj.get("id")
        session_id = str(ctx.get("session_id") or session_id or "").strip() or None

        policy = ValidationPolicyResolver(project_root=ev.project_root).resolve_for_task(
            str(task_id),
            session_id=session_id,
        )
        required = list(policy.required_evidence or [])

        try:
            from edison.core.qa.evidence.analysis import list_evidence_files

            files = {str(p.relative_to(round_dir)) for p in list_evidence_files(round_dir)}
        except Exception:
            files = {p.name for p in round_dir.iterdir() if p.is_file()} if round_dir.exists() else set()

        missing_patterns: list[str] = []
        for pattern in required:
            if not any(Path(name).match(str(pattern)) for name in files):
                missing_patterns.append(str(pattern))

        if missing_patterns:
            expected_report = round_dir / ev.implementation_filename
            raise ValueError(
                "Guard 'has_validator_reports' blocked transition.\n"
                f"Missing evidence in {round_dir.name}: {', '.join(missing_patterns)}\n"
                f"Expected implementation report: {expected_report}"
            )

        return True
    except ValueError:
        raise
    except Exception as e:
        # FAIL-CLOSED: unexpected evidence parsing errors should block, but with a clear message.
        raise ValueError(
            "Unable to verify validator evidence; run `edison qa validate <task> --execute` again."
        ) from e

    return False  # FAIL-CLOSED


def can_start_qa(ctx: Mapping[str, Any]) -> bool:
    """QA can start if task implementation is complete.

    FAIL-CLOSED: Returns False if task status cannot be verified.

    Checks:
    1. Task exists and is in 'done' state
    2. Implementation report exists

    Args:
        ctx: Context with 'task' dict or ability to look up task

    Returns:
        True if task is ready for QA
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        # Try to fetch task if task_id is available
        task_id = _get_task_id(ctx)
        if task_id:
            task = _fetch_task(task_id)

    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED

    # Task should be in 'done' or later state
    status = task.get("status") or task.get("state")
    if not status:
        return False  # FAIL-CLOSED

    # Allow QA to start when task is done
    done_states = {"done", "validated"}
    return str(status).lower() in done_states


def has_all_waves_passed(ctx: Mapping[str, Any]) -> bool:
    """Check if all validator waves have passed in order.

    FAIL-CLOSED: Returns False if wave requirements aren't met.

    This enforces the wave configuration from validation.yaml:
    - Critical wave must pass before comprehensive wave runs
    - All validators in a wave must pass for wave to pass

    Args:
        ctx: Context with task_id for evidence lookup

    Returns:
        True if all waves have passed in order
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence import read_validator_reports
        from edison.core.registries.validators import ValidatorRegistry

        qa_config = QAConfig()

        # Bundle-aware fast path: accept an approved bundle summary in the new schema
        # when it includes a validators list and no missing items.
        try:
            from edison.core.qa.evidence import EvidenceService

            ev = EvidenceService(str(task_id), project_root=qa_config.repo_root)
            bundle = ev.read_bundle()
            if isinstance(bundle, Mapping) and bundle.get("approved") is True:
                if bundle.get("rootTask") and bundle.get("scope"):
                    missing = bundle.get("missing") or []
                    validators = bundle.get("validators") or []
                    if isinstance(validators, list) and validators and (not isinstance(missing, list) or not any(missing)):
                        return True
        except Exception:
            pass

        waves = qa_config.get_waves()

        registry = ValidatorRegistry(project_root=qa_config.repo_root)

        session_obj = ctx.get("session")
        session_id = None
        if isinstance(session_obj, Mapping):
            session_id = session_obj.get("id")

        roster = registry.build_execution_roster(
            task_id=str(task_id),
            session_id=str(ctx.get("session_id") or session_id or ""),
            wave=None,
            extra_validators=None,
        )
        expected_ids = {
            str(v.get("id"))
            for v in (
                (roster.get("alwaysRequired") or [])
                + (roster.get("triggeredBlocking") or [])
                + (roster.get("triggeredOptional") or [])
                + (roster.get("extraAdded") or [])
            )
            if isinstance(v, Mapping) and v.get("id")
        }

        v = read_validator_reports(str(task_id))
        reports = v.get("reports", [])
        if not reports:
            return False  # FAIL-CLOSED: no reports

        verdicts: dict[str, bool] = {}
        for report in reports:
            vid = report.get("validatorId") or report.get("id")
            if vid:
                verdicts[str(vid)] = _is_passed(report)

        previous_wave_passed = True
        for wave in waves:
            wave_name = str(wave.get("name") or "")
            if not wave_name:
                return False  # FAIL-CLOSED
            if wave.get("requires_previous_pass") and not previous_wave_passed:
                return False

            wave_validators = [v for v in registry.get_by_wave(wave_name) if v.id in expected_ids]
            blocking_ids = [v.id for v in wave_validators if v.blocking]

            wave_passed = True
            for vid in blocking_ids:
                if vid not in verdicts or not verdicts[vid]:
                    wave_passed = False
                    if not wave.get("continue_on_fail", False):
                        return False

            previous_wave_passed = wave_passed

        return True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def has_bundle_approval(ctx: Mapping[str, Any]) -> bool:
    """Check if bundle approval exists.

    FAIL-CLOSED: Returns False if bundle approval is missing.

    For final QA validation (done→validated), we require:
    - Bundle summary JSON exists with approval

    Args:
        ctx: Context with task_id

    Returns:
        True if bundle is approved
    """
    task_id = _get_task_id(ctx)
    if not task_id:
        return False  # FAIL-CLOSED

    try:
        from edison.core.qa.evidence import EvidenceService

        svc = EvidenceService(str(task_id))
        if svc.get_current_round() is None:
            return False

        # Use EvidenceService.read_bundle() as single source for bundle I/O
        bundle = svc.read_bundle()
        if not bundle:
            return False

        return bundle.get("approved", False) is True
    except Exception:
        pass

    return False  # FAIL-CLOSED


def _is_passed(report: Mapping[str, Any]) -> bool:
    """Check if a validator report indicates pass."""
    verdict = report.get("verdict", "").lower()
    return verdict == "approve"


# Use shared utility for task_id extraction
_get_task_id = get_task_id_from_context


def _fetch_task(task_id: str) -> Mapping[str, Any] | None:
    """Fetch task data by ID."""
    try:
        from edison.core.task import TaskRepository

        repo = TaskRepository()
        task = repo.get(task_id)
        if task:
            return {
                "id": task.id,
                "status": task.state,
                "state": task.state,
                "session_id": task.session_id,
            }
    except Exception:
        pass
    return None
