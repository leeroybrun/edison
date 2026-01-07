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
from ..evidence import EvidenceService


enforce_no_legacy_project_root("lib.qa.bundler")


def bundle_summary_filename(config: Optional[Dict[str, Any]] = None) -> str:
    """Return the canonical validation summary filename.

    NOTE: `config` is accepted for backwards compatibility but ignored. Writers
    always emit the canonical filename (`validation-summary.md`) even if older
    configs still reference the legacy name.
    """
    return "validation-summary.md"


def bundle_summary_path(task_id: str, round_num: int, *, config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the full path to a bundle summary file.
    
    Args:
        task_id: Task identifier
        round_num: Validation round number
        config: Optional configuration dict
        
    Returns:
        Path to bundle summary file
    """
    ev_svc = EvidenceService(task_id)
    base = ev_svc.get_evidence_root()
    return base / f"round-{int(round_num)}" / ev_svc.bundle_filename


__all__ = [
    "bundle_summary_filename",
    "bundle_summary_path",
]
