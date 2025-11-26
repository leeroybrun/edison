"""Evidence path resolution logic."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .management import get_management_paths
from .resolver import EdisonPathError, resolve_project_root


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

    # If specific round requested, return it
    if round is not None:
        round_dir = evidence_base / f"round-{round}"
        if not round_dir.exists():
            raise EdisonPathError(
                f"Evidence round-{round} not found for task {task_id}: {round_dir}"
            )
        return round_dir

    # Find latest round
    rounds = sorted(
        [p for p in evidence_base.glob("round-*") if p.is_dir()],
        key=lambda p: int(p.name.split("-")[1])
        if p.name.split("-")[1].isdigit()
        else 0,
    )

    if not rounds:
        raise EdisonPathError(
            f"No evidence rounds found for task {task_id} in {evidence_base}"
        )

    return rounds[-1]


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

    if not evidence_base.exists():
        return []

    rounds = sorted(
        [p for p in evidence_base.glob("round-*") if p.is_dir()],
        key=lambda p: int(p.name.split("-")[1])
        if p.name.split("-")[1].isdigit()
        else 0,
    )

    return rounds


__all__ = [
    "find_evidence_round",
    "list_evidence_rounds",
]
