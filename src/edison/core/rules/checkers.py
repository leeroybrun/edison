"""
Rule-specific checker implementations.

This module contains specialized checker functions for individual rules.
Each checker validates whether a task satisfies specific rule requirements.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from ..paths import EdisonPathError, PathResolver
from ..paths.management import get_management_paths

from .models import Rule, RuleViolation
from .errors import RuleViolationError

if TYPE_CHECKING:
    from ..qa.evidence import EvidenceManager


def _load_json_safe(path: Path) -> Dict[str, Any]:
    """Safely load JSON from a file, returning empty dict on error."""
    from ..file_io.utils import read_json_with_default
    return read_json_with_default(path, default={})


def check_validator_approval(task: Dict[str, Any], rule: Rule) -> bool:
    """Check if task has a valid, recent validator bundle approval.

    Semantics (fail-closed, EvidenceManager-backed):
      - Locate bundle-approved.json for the latest evidence round:
          <management_dir>/qa/validation-evidence/<task-id>/round-N/bundle-approved.json
        using EvidenceManager (honours AGENTS_PROJECT_ROOT, project_ROOT, etc.).
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
            try:
                root = PathResolver.resolve_project_root()
            except EdisonPathError:
                # Fallback for partially migrated environments
                root = Path(__file__).resolve().parents[3]
            p = root / p
        bundle_path = p
    else:
        # Derive from evidence rounds when no explicit path is provided.
        if not require_report:
            # Config explicitly allows missing bundle; treat as pass.
            return True
        try:
            # Lazy import to avoid circular dependency
            from ..qa.evidence import EvidenceManager
            latest_round = EvidenceManager.get_latest_round_dir(str(task_id))
        except FileNotFoundError:
            # No evidence directory or no round-* dirs present.
            root = PathResolver.resolve_project_root()
            evidence_dir = get_management_paths(root).get_qa_root() / "validation-evidence" / str(task_id)
            try:
                rel = evidence_dir.relative_to(root)
            except Exception:
                rel = evidence_dir
            _raise(
                f"No evidence rounds found for task {task_id} under {rel}"
            )
        else:
            bundle_path = latest_round / "bundle-approved.json"

    # If we still do not have a path, treat as pass when not required.
    if bundle_path is None:
        return True

    # Sanity check existence
    if not bundle_path.exists():
        if require_report:
            _raise(
                f"Validation bundle summary missing for task {task_id}: {bundle_path} "
                "(bundle-approved.json not found)"
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

    # Content check: bundle-approved.json must contain approved: true
    data = _load_json_safe(bundle_path)
    if not data:
        if require_report:
            _raise(
                f"Invalid or empty bundle-approved.json for task {task_id}: "
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
            f"bundle-approved.json approved=false{details}"
        )

    return True


__all__ = [
    "check_validator_approval",
]
