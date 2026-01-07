"""
Rule-specific checker implementations.

This module contains specialized checker functions for individual rules.
Each checker validates whether a task satisfies specific rule requirements.

Architecture:
- Each checker is a function that takes (task, rule) and returns bool
- Checkers are registered in a global registry by rule ID
- The RulesEngine uses the registry instead of hardcoded dispatch
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.paths import get_management_paths

from .models import Rule, RuleViolation
from .errors import RuleViolationError

if TYPE_CHECKING:
    from ..qa.evidence import EvidenceService

# Type alias for checker functions
RuleChecker = Callable[[Dict[str, Any], Rule], bool]

# Global registry mapping rule IDs to checker functions
_RULE_CHECKERS: Dict[str, RuleChecker] = {}


def register_checker(rule_id: str) -> Callable[[RuleChecker], RuleChecker]:
    """Decorator to register a rule checker function.

    Args:
        rule_id: The rule ID this checker handles

    Returns:
        Decorator function

    Example:
        @register_checker("task-definition-complete")
        def check_task_definition(task: Dict, rule: Rule) -> bool:
            return bool(task.get("acceptanceCriteria"))
    """
    def decorator(func: RuleChecker) -> RuleChecker:
        _RULE_CHECKERS[rule_id] = func
        return func
    return decorator


def get_checker(rule_id: str) -> Optional[RuleChecker]:
    """Get the checker function for a rule ID.

    Args:
        rule_id: The rule ID to look up

    Returns:
        Checker function if registered, None otherwise
    """
    return _RULE_CHECKERS.get(rule_id)


@register_checker("validator-approval")
def check_validator_approval(task: Dict[str, Any], rule: Rule) -> bool:
    """Check if task has a valid, recent validator bundle approval.

    Semantics (fail-closed, EvidenceManager-backed):
      - Locate the bundle summary file for the latest evidence round:
          <management_dir>/qa/validation-reports/<task-id>/round-N/<bundleSummaryFile>
        using EvidenceService (honours AGENTS_PROJECT_ROOT and git root detection).
      - Require the bundle file to exist (requireReport=True) and be fresh
        based on maxAgeDays.
      - Require bundle.approved == True.
      - When approved == False, surface failing/missing validators in the error.

    Config (rule.config):
      - requireReport (bool, default True)
      - maxAgeDays (int, default 7)
    """
    # Normalize config with safe defaults
    cfg = rule.config if isinstance(getattr(rule, "config", None), dict) else {}
    require_report = bool(cfg.get("requireReport", True))
    try:
        max_age_days = int(cfg.get("maxAgeDays", 7))
    except Exception:
        max_age_days = 7

    task_id = str(task.get("id") or task.get("taskId") or "").strip() or "unknown"
    validation = task.get("validation") or {}
    explicit_path = validation.get("reportPath") or validation.get("path")

    def _raise(message: str) -> None:
        violation = RuleViolation(
            rule=rule,
            task_id=str(task_id),
            message=message,
            severity="blocking" if rule.blocking else "warning",
        )
        raise RuleViolationError(message, [violation])

    # ------------------------------------------------------------------
    # Resolve bundle path
    # ------------------------------------------------------------------
    bundle_path: Optional[Path] = None

    if explicit_path:
        # Caller provided an explicit report path on the task.
        p = Path(str(explicit_path))
        if not p.is_absolute():
            root = PathResolver.resolve_project_root()
            p = root / p
        bundle_path = p
    else:
        # Derive from evidence rounds when no explicit path is provided.
        if not require_report:
            # Config explicitly allows missing bundle; treat as pass.
            return True
        try:
            # Lazy import to avoid circular dependency
            from ..qa.evidence import EvidenceService
            svc = EvidenceService(str(task_id))
            current_round = svc.get_current_round()
            if current_round is None:
                raise FileNotFoundError(f"No evidence rounds found for {task_id}")
            latest_round = svc.ensure_round(current_round)
            # Use configured bundle filename from EvidenceService
            bundle_filename = svc.bundle_filename
        except FileNotFoundError:
            # No evidence directory or no round-* dirs present.
            from edison.core.qa._utils import get_evidence_base_path
            root = PathResolver.resolve_project_root()
            evidence_dir = get_evidence_base_path(root) / str(task_id)
            try:
                rel = evidence_dir.relative_to(root)
            except Exception:
                rel = evidence_dir
            _raise(
                f"No evidence rounds found for task {task_id} under {rel}"
            )
        else:
            bundle_path = latest_round / bundle_filename

    # If we still do not have a path, treat as pass when not required.
    if bundle_path is None:
        return True

    # Sanity check existence
    if not bundle_path.exists():
        # Backward compatibility: prefer the configured/new filename, but allow
        # legacy `bundle-summary.md` to satisfy the approval requirement.
        legacy_path = bundle_path.with_name("bundle-summary.md")
        if legacy_path != bundle_path and legacy_path.exists():
            bundle_path = legacy_path
        else:
            if require_report:
                _raise(
                    f"Validation bundle summary missing for task {task_id}: {bundle_path} "
                    f"({bundle_path.name} not found)"
                )
            return False

    # Age check (mtime)
    try:
        mtime = datetime.fromtimestamp(bundle_path.stat().st_mtime, tz=timezone.utc)
    except Exception:
        # Preserve previous fail-open semantics on timestamp issues.
        mtime = datetime.now(timezone.utc)
    age_ok = (datetime.now(timezone.utc) - mtime) <= timedelta(days=max_age_days)
    if not age_ok:
        _raise(
            f"Validation bundle summary expired for task {task_id}: {bundle_path} "
            f"(older than {max_age_days} days)"
        )

    # Content check: bundle summary must contain approved: true (YAML frontmatter)
    from edison.core.qa.evidence.report_io import read_structured_report
    data = read_structured_report(bundle_path)
    if not data:
        if require_report:
            _raise(
                f"Invalid or empty {bundle_path.name} for task {task_id}: "
                f"{bundle_path}"
            )
        return False

    approved = bool(data.get("approved"))
    if not approved:
        # Derive failing/missing validators from bundle payload for diagnostics.
        failing_validators: list[str] = []

        validators = data.get("validators") or []
        if isinstance(validators, list):
            for entry in validators:
                if not isinstance(entry, dict):
                    continue
                vid = str(
                    entry.get("validatorId") or entry.get("id") or ""
                ).strip()
                v_approved = entry.get("approved")
                verdict = str(entry.get("verdict") or "").lower()
                if v_approved is False or verdict in {"reject", "blocked"}:
                    if vid:
                        failing_validators.append(vid)

        missing = data.get("missing") or []
        if isinstance(missing, list):
            for m in missing:
                if m:
                    failing_validators.append(str(m))

        details = ""
        if failing_validators:
            uniq = sorted({v for v in failing_validators})
            details = f"; failing or missing validators: {', '.join(uniq)}"

        _raise(
            f"Validation bundle not approved for task {task_id}: "
            f"{bundle_path.name} approved=false{details}"
        )

    return True


@register_checker("task-definition-complete")
def check_task_definition_complete(task: Dict[str, Any], rule: Rule) -> bool:
    """Check if task has acceptance criteria defined."""
    return bool(task.get("acceptanceCriteria"))


@register_checker("all-tests-pass")
def check_all_tests_pass(task: Dict[str, Any], rule: Rule) -> bool:
    """Check if all tests pass for the task."""
    test_status = task.get("testStatus", {})
    return bool(test_status.get("allPass", False))


@register_checker("coverage-threshold")
def check_coverage_threshold(task: Dict[str, Any], rule: Rule) -> bool:
    """Check if code coverage meets the threshold."""
    coverage = task.get("coverage", {})
    return bool(coverage.get("meetsThreshold", False))


__all__ = [
    "check_validator_approval",
    "register_checker",
    "get_checker",
    "RuleChecker",
]
