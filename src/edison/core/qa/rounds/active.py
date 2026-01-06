"""Canonical "active round" selection for QA validation.

Round numbers are stored as `round-N/` directories under the per-task QA reports
root. A round becomes *finalized* when its `validation-summary.md` frontmatter
contains `status: final`.

This module centralizes:
- round discovery
- finalized vs active detection
- selection rules used by CLI flows (prepare/validate/summarize)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from edison.core.qa.evidence import EvidenceService


RoundStatus = Literal["draft", "final"]


@dataclass(frozen=True)
class ActiveRound:
    task_id: str
    round_num: int
    status: RoundStatus
    round_dir: Path


def _normalize_status(value: object) -> RoundStatus | None:
    raw = str(value or "").strip().lower()
    if raw in {"draft"}:
        return "draft"
    if raw in {"final", "finalized"}:
        return "final"
    return None


def round_status(*, project_root: Path, task_id: str, round_num: int) -> RoundStatus:
    """Return the status for a round (draft by default).

    Rules:
    - If no summary file exists for the round, treat it as `draft` (open).
    - If a summary file exists and has `status: draft|final`, respect it.
    - If a summary file exists but has no explicit status, treat it as `final`
      (legacy rounds should not be reused as active).
    """
    ev = EvidenceService(task_id, project_root=project_root)
    round_dir = ev.get_round_dir(int(round_num))

    # Missing summary file => open round.
    candidates = [
        round_dir / "validation-summary.md",
        round_dir / ev.bundle_filename,
        round_dir / "bundle-summary.md",
    ]
    existing = next((p for p in candidates if p.exists()), None)
    if existing is None:
        return "draft"

    data = {}
    try:
        data = ev.read_bundle(round_num) or {}
    except Exception:
        data = {}

    status = _normalize_status((data or {}).get("status"))
    if status is not None:
        return status

    # Backwards-compat: older rounds may not have an explicit status field. Treat
    # them as finalized to avoid reusing legacy rounds as "active".
    return "final"


def latest_round_num(*, project_root: Path, task_id: str) -> int | None:
    """Return the latest existing round number for task_id, if any."""
    ev = EvidenceService(task_id, project_root=project_root)
    current = ev.get_current_round()
    return int(current) if current is not None else None


def active_round(*, project_root: Path, task_id: str) -> ActiveRound | None:
    """Return the current active (not finalized) round, if any."""
    latest = latest_round_num(project_root=project_root, task_id=task_id)
    if latest is None:
        return None

    ev = EvidenceService(task_id, project_root=project_root)
    round_dir = ev.get_round_dir(int(latest))
    if not round_dir.exists():
        return None

    status = round_status(project_root=project_root, task_id=task_id, round_num=int(latest))
    if status == "final":
        return None
    return ActiveRound(task_id=str(task_id), round_num=int(latest), status=status, round_dir=round_dir)


def is_round_final(*, project_root: Path, task_id: str, round_num: int) -> bool:
    return round_status(project_root=project_root, task_id=task_id, round_num=int(round_num)) == "final"


__all__ = ["ActiveRound", "RoundStatus", "active_round", "is_round_final", "latest_round_num", "round_status"]
