"""QA round management helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..legacy_guard import enforce_no_legacy_project_root
from . import evidence


enforce_no_legacy_project_root("lib.qa.rounds")


def round_dir(task_id: str, round_num: int) -> Path:
    base = evidence.get_evidence_dir(task_id)
    return base / f"round-{int(round_num)}"


def latest_round(task_id: str) -> Optional[int]:
    return evidence.get_latest_round(task_id)


def next_round(task_id: str) -> int:
    latest = latest_round(task_id)
    return (latest or 0) + 1


__all__ = ["round_dir", "latest_round", "next_round"]

