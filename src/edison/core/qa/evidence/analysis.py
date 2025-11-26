"""Analysis functions for evidence data."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from ...utils.paths import PathResolver
from edison.core.utils.io import read_json
from .helpers import _task_evidence_root, list_evidence_files


def missing_evidence_blockers(task_id: str) -> List[Dict[str, Any]]:
    """Return automation blockers for missing evidence for a given task."""
    evidence_root = _task_evidence_root(task_id)
    project_root = PathResolver.resolve_project_root()
    try:
        evidence_rel = str(evidence_root.relative_to(project_root))
    except Exception:
        evidence_rel = str(evidence_root)
    if not evidence_root.exists():
        return [
            {
                "kind": "automation",
                "recordId": task_id,
                "message": f"Evidence dir missing: {evidence_rel}",
                "fixCmd": ["mkdir", "-p", f"{evidence_rel}/round-1"],
            }
        ]
    rounds = sorted(
        [p for p in evidence_root.glob("round-*") if p.is_dir()],
        key=lambda p: p.name,
    )
    if not rounds:
        return [
            {
                "kind": "automation",
                "recordId": task_id,
                "message": "No round-* directories present",
                "fixCmd": ["mkdir", "-p", f"{evidence_rel}/round-1"],
            }
        ]
    latest = rounds[-1]
    needed = {"command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"}
    present = {p.name for p in latest.iterdir() if p.is_file()}
    missing = sorted(needed - present)
    if not missing:
        return []
    return [
        {
            "kind": "automation",
            "recordId": task_id,
            "message": f"Missing evidence files in {latest.name}: {', '.join(missing)}",
        }
    ]


def read_validator_jsons(task_id: str) -> Dict[str, Any]:
    """Return latest validator-* JSON reports for a task."""
    root = _task_evidence_root(task_id)
    out: Dict[str, Any] = {"round": None, "reports": []}
    if not root.exists():
        return out
    rounds = sorted([p for p in root.glob("round-*") if p.is_dir()], key=lambda p: p.name)
    if not rounds:
        return out
    latest = rounds[-1]
    out["round"] = latest.name
    for p in latest.glob("validator-*-report.json"):
        try:
            data = read_json(p)
            out["reports"].append(data)
        except Exception:
            continue
    return out


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
