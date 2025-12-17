"""Promotion helpers shared by QA workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ..legacy_guard import enforce_no_legacy_project_root
from .evidence import EvidenceService
from .evidence import reports as reportlib


enforce_no_legacy_project_root("lib.qa.promoter")


def should_revalidate_bundle(bundle_path: Path, validator_reports: Iterable[Path], task_files: Iterable[Path]) -> bool:
    """Return True when bundle re-validation is required."""
    try:
        if not bundle_path.exists():
            return True
        bundle_mtime = bundle_path.stat().st_mtime
        for rp in validator_reports:
            try:
                if rp.exists() and rp.stat().st_mtime > bundle_mtime:
                    return True
            except FileNotFoundError:
                return True
        for f in task_files:
            try:
                if f.exists() and f.stat().st_mtime > bundle_mtime:
                    return True
            except FileNotFoundError:
                return True
        return False
    except Exception:
        return True


def collect_validator_reports(task_ids: Iterable[str]) -> List[Path]:
    """Collect all validator reports across tasks using EvidenceService."""
    reports: List[Path] = []
    for tid in task_ids:
        ev_svc = EvidenceService(tid)
        if not ev_svc.get_evidence_root().exists():
            continue
        # Use EvidenceService.list_rounds() instead of importing from rounds.py
        for rd in ev_svc.list_rounds():
            reports.extend(reportlib.list_validator_reports(rd))
    return reports


def collect_task_files(task_ids: Iterable[str], session_id: Optional[str] = None) -> List[Path]:
    from edison.core.task import TaskRepository

    task_repo = TaskRepository()
    files: List[Path] = []
    for tid in task_ids:
        try:
            files.append(task_repo.get_path(tid))
        except FileNotFoundError:
            pass
    return files


__all__ = [
    "should_revalidate_bundle",
    "collect_validator_reports",
    "collect_task_files",
]
