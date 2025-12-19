"""Follow-up loading logic.

Uses EvidenceService as the single source for evidence I/O.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .service import EvidenceService


def load_impl_followups(task_id: str) -> List[Dict[str, Any]]:
    """Load follow-up tasks from implementation report for latest round.

    Uses EvidenceService.read_implementation_report() for I/O.
    """
    ev_svc = EvidenceService(task_id)
    if ev_svc.get_current_round_dir() is None:
        return []

    # Use EvidenceService for reading (handles config-based filename)
    data = ev_svc.read_implementation_report()
    if not data:
        return []

    out: List[Dict[str, Any]] = []
    for it in data.get("followUpTasks", []) or []:
        out.append(
            {
                "source": "implementation",
                "title": it.get("title"),
                "blockingBeforeValidation": bool(it.get("blockingBeforeValidation", False)),
                "claimNow": bool(it.get("claimNow", False)),
                "category": it.get("category"),
            }
        )
    return out


def load_bundle_followups(task_id: str) -> List[Dict[str, Any]]:
    """Load non-blocking follow-ups from the bundle summary for latest round.

    Uses EvidenceService.read_bundle() for I/O.
    """
    ev_svc = EvidenceService(task_id)
    if ev_svc.get_current_round_dir() is None:
        return []

    # Use EvidenceService for reading (handles config-based filename)
    data = ev_svc.read_bundle()
    if not data:
        return []

    out: List[Dict[str, Any]] = []
    for it in data.get("nonBlockingFollowUps", []) or []:
        out.append(
            {
                "source": "validator",
                "title": it.get("title"),
                "blockingBeforeValidation": False,
                "claimNow": False,
                "category": it.get("category"),
            }
        )
    return out
