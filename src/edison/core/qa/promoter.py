"""Promotion helpers shared by QA workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ..legacy_guard import enforce_no_legacy_project_root
from . import evidence


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
    reports: List[Path] = []
    for tid in task_ids:
        base = evidence.get_evidence_dir(tid)
        if not base.exists():
            continue
        for rd in sorted([p for p in base.glob("round-*") if p.is_dir()], key=lambda p: p.name):
            reports.extend(sorted(rd.glob("validator-*-report.json")))
    return reports


def collect_task_files(task_ids: Iterable[str], session_id: Optional[str] = None) -> List[Path]:
    from .. import task  # type: ignore

    files: List[Path] = []
    for tid in task_ids:
        try:
            files.append(task.find_record(tid, "task", session_id=session_id))
        except FileNotFoundError:
            pass
        try:
            files.append(task.find_record(tid, "qa", session_id=session_id))
        except FileNotFoundError:
            pass
    return files


__all__ = [
    "should_revalidate_bundle",
    "collect_validator_reports",
    "collect_task_files",
]

