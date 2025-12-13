"""Validation bundle path helpers.

NOTE: Bundle I/O operations are now centralized in EvidenceService.
This module only provides path resolution utilities.

Use EvidenceService for reading/writing bundles:
    from edison.core.qa.evidence import EvidenceService
    
    ev_svc = EvidenceService(task_id)
    bundle = ev_svc.read_bundle(round_num)
    ev_svc.write_bundle(bundle_data, round_num)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ...legacy_guard import enforce_no_legacy_project_root
from edison.core.config.domains.qa import QAConfig
from ..evidence import EvidenceService


enforce_no_legacy_project_root("lib.qa.bundler")


def bundle_summary_filename(config: Optional[Dict[str, Any]] = None) -> str:
    """Get the bundle summary filename from configuration.
    
    Args:
        config: Optional configuration dict (defaults to QAConfig)
        
    Returns:
        Bundle summary filename string
        
    Raises:
        RuntimeError: If bundleSummaryFile not configured
    """
    cfg = config or QAConfig().validation_config
    if isinstance(cfg, dict) and "artifactPaths" not in cfg and "validation" in cfg:
        cfg = cfg.get("validation", {}) or {}
    paths = cfg.get("artifactPaths", {}) if isinstance(cfg, dict) else {}
    name = paths.get("bundleSummaryFile") if isinstance(paths, dict) else None
    if not name:
        raise RuntimeError(
            "validation.artifactPaths.bundleSummaryFile missing in configuration"
        )
    return str(name)


def bundle_summary_path(task_id: str, round_num: int, *, config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the full path to a bundle summary file.
    
    Args:
        task_id: Task identifier
        round_num: Validation round number
        config: Optional configuration dict
        
    Returns:
        Path to bundle summary file
    """
    filename = bundle_summary_filename(config)
    ev_svc = EvidenceService(task_id)
    base = ev_svc.get_evidence_root()
    return base / f"round-{int(round_num)}" / filename


__all__ = [
    "bundle_summary_filename",
    "bundle_summary_path",
]
