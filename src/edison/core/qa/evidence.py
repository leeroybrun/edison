from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ..evidence import EvidenceManager, _task_evidence_root
from ..io_utils import read_json_safe as io_read_json_safe


def get_evidence_dir(task_id: str) -> Path:
    """Return the canonical evidence directory for a task."""
    return _task_evidence_root(task_id)


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
            data = io_read_json_safe(meta)
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


def has_required_evidence(base: Path, required: Iterable[str]) -> bool:
    """
    Return True when all required evidence file patterns are present.

    Args:
        base: Evidence root directory.
        required: Iterable of glob-style patterns relative to ``base``.
    """
    base = Path(base)
    files = {str(p.relative_to(base)) for p in list_evidence_files(base)}
    for pattern in required:
        matched = any(Path(name).match(pattern) for name in files)
        if not matched:
            return False
    return True


__all__ = [
    "get_evidence_dir",
    "get_latest_round",
    "get_implementation_report_path",
    "list_evidence_files",
    "has_required_evidence",
]
