"""Follow-up loading logic."""
from __future__ import annotations

from typing import Any, Dict, List

from edison.core.utils.io import read_json
from .helpers import _latest_round_dir


def load_impl_followups(task_id: str) -> List[Dict[str, Any]]:
    """Load follow-up tasks from implementation-report.json for latest round."""
    rd = _latest_round_dir(task_id)
    if not rd:
        return []
    rp = rd / "implementation-report.json"
    if not rp.exists():
        return []
    try:
        data = read_json(rp)
    except Exception:
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
    """Load non-blocking follow-ups from bundle-approved.json for latest round."""
    rd = _latest_round_dir(task_id)
    if not rd:
        return []
    bp = rd / "bundle-approved.json"
    if not bp.exists():
        return []
    try:
        data = read_json(bp)
    except Exception:
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
