"""Analysis functions for evidence data."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from edison.core.utils.paths import PathResolver
from .report_io import read_structured_report
from edison.core.config.domains.qa import QAConfig
from .service import EvidenceService


def list_evidence_files(base: Path) -> List[Path]:
    """Return a sorted list of evidence files underneath base.

    Only regular files are returned; directories are ignored.
    """
    base = Path(base)
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file())


def missing_evidence_blockers(task_id: str) -> List[Dict[str, Any]]:
    """Return automation blockers for missing evidence for a given task."""
    ev_svc = EvidenceService(task_id)
    evidence_root = ev_svc.get_evidence_root()
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
                "fixCmd": ["edison", "qa", "round", "prepare", task_id],
            }
        ]
    rounds = ev_svc.list_rounds()
    if not rounds:
        return [
            {
                "kind": "automation",
                "recordId": task_id,
                "message": "No round-* directories present",
                "fixCmd": ["edison", "qa", "round", "prepare", task_id],
            }
        ]
    latest = rounds[-1]

    # Preset-aware required evidence (single source via policy resolver).
    try:
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=project_root)
        # IMPORTANT: if there is no implementation report yet, do not infer the preset
        # from arbitrary git status dirt (which may include project scaffolding).
        # Fail closed to the configured default preset, or "standard" if none.
        preset_override: str | None = None
        try:
            report = ev_svc.read_implementation_report()
        except Exception:
            report = None

        if not report:
            try:
                configured_default = QAConfig(repo_root=project_root).validation_config.get("defaultPreset")
                configured_default = str(configured_default).strip() if configured_default else ""
            except Exception:
                configured_default = ""
            preset_override = configured_default or "standard"

        policy = resolver.resolve_for_task(task_id, preset_name=preset_override)
        required_files = list(policy.required_evidence or [])
    except Exception:
        # Fail-closed: if policy resolution fails, require baseline evidence.
        try:
            required_files = QAConfig(repo_root=project_root).get_required_evidence_files()
        except Exception:
            required_files = []

    needed = set(required_files)
    qa_cfg = QAConfig(repo_root=project_root)
    evidence_files_cfg = (qa_cfg.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
    if not isinstance(evidence_files_cfg, dict):
        evidence_files_cfg = {}
    command_evidence_names = set(str(v).strip() for v in evidence_files_cfg.values() if str(v).strip())

    command_required = [
        str(p)
        for p in required_files
        if str(p).startswith("command-") or str(p) in command_evidence_names
    ]
    round_required = [str(p) for p in required_files if str(p) not in set(command_required)]

    missing: list[str] = []
    if round_required:
        try:
            files = {str(p.relative_to(latest)) for p in list_evidence_files(latest)}
        except Exception:
            files = {p.name for p in latest.iterdir() if p.is_file()}
        for pattern in round_required:
            if not any(Path(name).match(str(pattern)) for name in files):
                missing.append(str(pattern))

    if command_required:
        from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_status

        key = current_snapshot_key(project_root=project_root)
        snap = snapshot_status(project_root=project_root, key=key, required_files=command_required)
        for f in (snap.get("missing") or []):
            missing.append(str(f))
    if not missing:
        return []
    return [
        {
            "kind": "automation",
            "recordId": task_id,
            "message": f"Missing evidence files: {', '.join(missing)}",
        }
    ]


def read_validator_reports(task_id: str) -> Dict[str, Any]:
    """Return latest validator reports for a task (Markdown+frontmatter)."""
    ev_svc = EvidenceService(task_id)
    out: Dict[str, Any] = {"round": None, "reports": []}

    latest = ev_svc.get_current_round_dir()
    if not latest:
        return out

    out["round"] = latest.name
    for p in ev_svc.list_validator_reports(round_num=ev_svc.get_current_round() or None):
        data = read_structured_report(p)
        if data:
            out["reports"].append(data)
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
