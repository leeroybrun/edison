"""Evidence path resolution logic.

This module provides high-level evidence path resolution using task IDs.
All round logic is delegated to EvidenceService as the single source.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .management import get_management_paths
from .errors import EdisonPathError
from .resolver import resolve_project_root


def _get_evidence_service(task_id: str):
    """Lazy import to avoid circular dependency."""
    from edison.core.qa.evidence import EvidenceService
    return EvidenceService(task_id)


def find_evidence_round(
    task_id: str,
    round: Optional[int] = None,
) -> Path:
    """Evidence directory resolution with round detection.

    Resolution logic:
    - If round is specified: .project/qa/validation-evidence/{task_id}/round-{round}/
    - If round is None: Find latest round-N directory

    Args:
        task_id: Task ID (e.g., "task-100" or "100")
        round: Specific round number, or None for latest

    Returns:
        Path: Evidence directory path

    Raises:
        EdisonPathError: If evidence directory not found
    """
    from edison.core.qa._utils import get_evidence_base_path
    root = resolve_project_root()
    evidence_base = get_evidence_base_path(root) / task_id

    if not evidence_base.exists():
        raise EdisonPathError(f"Evidence directory does not exist: {evidence_base}")

    # Use EvidenceService for round resolution
    ev_svc = _get_evidence_service(task_id)
    
    if round is not None:
        round_dir = ev_svc.get_round_dir(round)
        if not round_dir.exists():
            raise EdisonPathError(
                f"Evidence round-{round} not found for task {task_id}"
            )
        return round_dir
    else:
        round_dir = ev_svc.get_current_round_dir()
        if round_dir is None:
            raise EdisonPathError(
                f"No evidence rounds found for task {task_id} in {evidence_base}"
            )
        return round_dir


def list_evidence_rounds(task_id: str) -> List[Path]:
    """List all evidence round directories for a task.

    Args:
        task_id: Task ID

    Returns:
        List[Path]: Sorted list of round directories (oldest to newest)
    """
    # Use EvidenceService for round listing
    ev_svc = _get_evidence_service(task_id)
    return ev_svc.list_rounds()


__all__ = [
    "find_evidence_round",
    "list_evidence_rounds",
]



