"""Evidence path resolution logic.

This module provides high-level evidence path resolution using task IDs.
Core round directory logic is delegated to qa.evidence.rounds module.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .management import get_management_paths
from .resolver import EdisonPathError, resolve_project_root


def _get_round_functions():
    """Lazy import to avoid circular dependency."""
    from edison.core.qa.evidence.rounds import list_round_dirs, resolve_round_dir
    return list_round_dirs, resolve_round_dir


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
    root = resolve_project_root()
    mgmt_paths = get_management_paths(root)
    evidence_base = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

    if not evidence_base.exists():
        raise EdisonPathError(f"Evidence directory does not exist: {evidence_base}")

    # Delegate to canonical round resolution (lazy import to avoid circular dependency)
    _, resolve_round_dir = _get_round_functions()
    round_dir = resolve_round_dir(evidence_base, round_num=round)

    if round_dir is None:
        if round is not None:
            raise EdisonPathError(
                f"Evidence round-{round} not found for task {task_id}"
            )
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
    root = resolve_project_root()
    mgmt_paths = get_management_paths(root)
    evidence_base = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

    # Delegate to canonical round listing (lazy import to avoid circular dependency)
    list_round_dirs, _ = _get_round_functions()
    return list_round_dirs(evidence_base)


__all__ = [
    "find_evidence_round",
    "list_evidence_rounds",
]



