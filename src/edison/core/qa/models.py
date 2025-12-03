"""QA entity models.

This module defines the QARecord dataclass and related types for the QA
domain. QA records track validation status of tasks through the QA workflow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    EntityMetadata,
    StateHistoryEntry,
)


@dataclass  
class QARecord:
    """A QA record entity for task validation.
    
    QA records track the validation status of tasks.
    State is derived from directory location, NOT stored in the model.
    
    Attributes:
        id: Unique QA record identifier
        task_id: Associated task identifier
        state: Current QA state (derived from directory location)
        title: QA title/summary
        session_id: Associated session identifier (optional)
        validator_owner: Owner/validator responsible for this QA
        metadata: Entity metadata
        state_history: List of state transitions
        validators: List of validators that have run
        evidence: List of evidence file paths
        round: Current validation round number
    """
    id: str
    task_id: str
    state: str
    title: str
    session_id: Optional[str] = None
    validator_owner: Optional[str] = None
    metadata: EntityMetadata = field(default_factory=lambda: EntityMetadata.create())
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    validators: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    round: int = 1
    
    def record_transition(
        self,
        from_state: str,
        to_state: str,
        *,
        reason: Optional[str] = None,
        violations: Optional[List[str]] = None,
    ) -> None:
        """Record a state transition in history."""
        entry = StateHistoryEntry.create(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            violations=violations,
        )
        self.state_history.append(entry)
        self.metadata.touch()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data: Dict[str, Any] = {
            "id": self.id,
            "task_id": self.task_id,
            "state": self.state,
            "title": self.title,
        }
        
        if self.session_id:
            data["session_id"] = self.session_id
        
        if self.validator_owner:
            data["validator_owner"] = self.validator_owner
        
        data["metadata"] = self.metadata.to_dict()
        
        if self.state_history:
            data["state_history"] = [h.to_dict() for h in self.state_history]
        
        if self.validators:
            data["validators"] = self.validators
        
        if self.evidence:
            data["evidence"] = self.evidence
        
        data["round"] = self.round
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QARecord":
        """Create QARecord from dictionary representation."""
        metadata_data = data.get("metadata", {})
        metadata = EntityMetadata.from_dict(metadata_data)
        
        # Support both snake_case and camelCase
        history_data = data.get("state_history") or data.get("stateHistory", [])
        state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
        
        return cls(
            id=data.get("id", ""),
            task_id=data.get("task_id") or data.get("taskId", ""),
            state=data.get("state") or data.get("status") or "todo",
            title=data.get("title", ""),
            session_id=data.get("session_id") or data.get("sessionId"),
            validator_owner=data.get("validator_owner") or data.get("validatorOwner"),
            metadata=metadata,
            state_history=state_history,
            validators=data.get("validators", []),
            evidence=data.get("evidence", []),
            round=data.get("round", 1),
        )
    
    @classmethod
    def create(
        cls,
        qa_id: str,
        task_id: str,
        title: str,
        *,
        session_id: Optional[str] = None,
        validator_owner: Optional[str] = None,
        state: str = "todo",
    ) -> "QARecord":
        """Factory method to create a new QA record."""
        return cls(
            id=qa_id,
            task_id=task_id,
            state=state,
            title=title,
            session_id=session_id,
            validator_owner=validator_owner,
            metadata=EntityMetadata.create(session_id=session_id),
        )


__all__ = [
    "QARecord",
]

