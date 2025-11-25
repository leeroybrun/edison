"""
Session domain models.

Data structures defined here provide a focused surface area for
session-related records. The underlying representations are currently
mirrored in ``sessionlib`` and will be consolidated here during the
GREEN/REFACTOR phases.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionPaths:
    """Simple container for key session paths."""

    session_id: str
    path: Path
    status_dir: Path


@dataclass
class TaskEntry:
    """In-memory representation of a task registered against a session."""

    record_id: str
    status: str
    owner: str
    qa_id: Optional[str] = None
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    claimed_at: Optional[str] = None
    last_active: Optional[str] = None
    automation: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry into the JSON-compatible schema."""
        return {
            "recordId": self.record_id,
            "status": self.status,
            "owner": self.owner,
            "qaId": self.qa_id,
            "parentId": self.parent_id,
            "childIds": list(self.child_ids),
            "claimedAt": self.claimed_at,
            "lastActive": self.last_active,
            "automation": dict(self.automation),
            "notes": list(self.notes),
        }


@dataclass
class QAEntry:
    """In-memory representation of a QA record within a session."""

    record_id: str
    task_id: str
    status: str
    round: int = 1
    evidence: List[str] = field(default_factory=list)
    validators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry into the JSON-compatible schema."""
        return {
            "recordId": self.record_id,
            "taskId": self.task_id,
            "status": self.status,
            "round": self.round,
            "evidence": list(self.evidence),
            "validators": list(self.validators),
        }


__all__ = ["SessionPaths", "TaskEntry", "QAEntry"]

