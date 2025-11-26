"""Helper functions for evidence path resolution and directory management."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ...paths import PathResolver
from ...paths.management import get_management_paths
from ...file_io.utils import read_json_safe


def _task_evidence_root(task_id: str) -> Path:
    root = PathResolver.resolve_project_root()
    mgmt_paths = get_management_paths(root)
    return mgmt_paths.get_qa_root() / "validation-evidence" / task_id


def get_evidence_dir(task_id: str) -> Path:
    """Return the canonical evidence directory for a task."""
    return _task_evidence_root(task_id)


def _latest_round_dir(task_id: str) -> Optional[Path]:
    root = _task_evidence_root(task_id)
    if not root.exists():
        return None
    rounds = [p for p in root.glob("round-*") if p.is_dir()]
    if not rounds:
        return None
    return sorted(rounds, key=lambda p: p.name)[-1]


def get_latest_round(task_id: str) -> Optional[int]:
    """Return the latest evidence round number for a task, or None.

    Resolution order mirrors the legacy QA scripts:
    1. Prefer ``metadata.json`` when it contains a valid ``currentRound`` or
       ``round`` integer and the corresponding directory exists.
    2. Fall back to the highest numeric ``round-N`` directory under the
       task's evidence root.
    """
    root = _task_evidence_root(task_id)
    if not root.exists():
        return None

    meta = root / "metadata.json"
    try:
        if meta.exists():
            data = read_json_safe(meta)
            if isinstance(data, dict):
                for key in ("currentRound", "round"):
                    value = data.get(key)
                    if isinstance(value, int):
                        candidate = root / f"round-{value}"
                        if candidate.is_dir():
                            return int(value)
    except Exception:
        # Fall back to scanning directories when metadata is missing/invalid.
        pass

    rounds = [p for p in root.glob("round-*") if p.is_dir()]
    if not rounds:
        return None

    def _key(p: Path) -> tuple[int, str]:
        try:
            return (int(p.name.split("-", 1)[1]), p.name)
        except Exception:
            return (0, p.name)

    latest = sorted(rounds, key=_key)[-1]
    # We know latest follows round-N naming; extract N.
    try:
        return int(latest.name.split("-", 1)[1])
    except Exception:
        return None


def get_implementation_report_path(task_id: str, round_num: int) -> Path:
    """Return the path to the implementation report for a given round."""
    return get_evidence_dir(task_id) / f"round-{round_num}" / "implementation-report.json"


def list_evidence_files(base: Path) -> List[Path]:
    """
    Return a sorted list of evidence files underneath ``base``.

    Only regular files are returned; directories are ignored.
    """
    base = Path(base)
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file())
