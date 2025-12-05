"""Base entity types and metadata.

This module provides the foundational data structures for entities:
- EntityMetadata: Common metadata fields (timestamps, ownership)
- EntityId: Type alias for entity identifiers
- StateHistoryEntry: Record of state transitions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edison.core.utils.time import utc_timestamp


# Type alias for entity identifiers
EntityId = str


@dataclass
class EntityMetadata:
    """Common metadata for all entities.
    
    Attributes:
        created_at: ISO timestamp when entity was created
        updated_at: ISO timestamp when entity was last updated
        created_by: Owner/creator identifier (optional)
        session_id: Associated session identifier (optional)
    """
    created_at: str
    updated_at: str
    created_by: Optional[str] = None
    session_id: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        *,
        created_by: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "EntityMetadata":
        """Create new metadata with current timestamp.
        
        Args:
            created_by: Optional owner/creator identifier
            session_id: Optional session identifier
            
        Returns:
            New EntityMetadata instance
        """
        now = utc_timestamp()
        return cls(
            created_at=now,
            updated_at=now,
            created_by=created_by,
            session_id=session_id,
        )
    
    def touch(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = utc_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "createdBy": self.created_by,
            "sessionId": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityMetadata":
        """Create from dictionary representation.
        
        Supports both camelCase and snake_case keys for compatibility.
        """
        return cls(
            created_at=data.get("createdAt") or data.get("created_at") or utc_timestamp(),
            updated_at=data.get("updatedAt") or data.get("updated_at") or utc_timestamp(),
            created_by=data.get("createdBy") or data.get("created_by"),
            session_id=data.get("sessionId") or data.get("session_id"),
        )


@dataclass
class StateHistoryEntry:
    """Record of a state transition.
    
    Attributes:
        from_state: Previous state
        to_state: New state
        timestamp: When transition occurred
        reason: Optional reason for transition
        violations: List of rule violations (warnings)
    """
    from_state: str
    to_state: str
    timestamp: str
    reason: Optional[str] = None
    violations: List[str] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        from_state: str,
        to_state: str,
        *,
        reason: Optional[str] = None,
        violations: Optional[List[str]] = None,
    ) -> "StateHistoryEntry":
        """Create a new history entry with current timestamp."""
        return cls(
            from_state=from_state,
            to_state=to_state,
            timestamp=utc_timestamp(),
            reason=reason,
            violations=violations or [],
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "from": self.from_state,
            "to": self.to_state,
            "timestamp": self.timestamp,
        }
        if self.reason:
            result["reason"] = self.reason
        if self.violations:
            result["ruleViolations"] = self.violations
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateHistoryEntry":
        """Create from dictionary representation."""
        return cls(
            from_state=data.get("from", ""),
            to_state=data.get("to", ""),
            timestamp=data.get("timestamp", ""),
            reason=data.get("reason"),
            violations=data.get("ruleViolations", []),
        )


@dataclass
class BaseEntity:
    """Base class providing common entity structure.
    
    This is a dataclass that can be subclassed by specific entity types
    (Task, Session, QARecord, etc.) to inherit common fields.
    
    Attributes:
        id: Unique entity identifier
        state: Current entity state
        metadata: Entity metadata (timestamps, ownership)
        state_history: List of state transitions
    """
    id: EntityId
    state: str
    metadata: EntityMetadata
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    
    def record_transition(
        self,
        from_state: str,
        to_state: str,
        *,
        reason: Optional[str] = None,
        violations: Optional[List[str]] = None,
    ) -> None:
        """Record a state transition in history.
        
        Args:
            from_state: Previous state
            to_state: New state  
            reason: Optional reason for transition
            violations: Optional list of rule violations
        """
        entry = StateHistoryEntry.create(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            violations=violations,
        )
        self.state_history.append(entry)
        self.metadata.touch()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Subclasses should override and call super().to_dict()
        to include their additional fields.
        """
        return {
            "id": self.id,
            "state": self.state,
            "metadata": self.metadata.to_dict(),
            "stateHistory": [h.to_dict() for h in self.state_history],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """Create from dictionary representation.
        
        Note: Subclasses should override this method to handle
        their additional fields and state defaults.
        """
        history_data = data.get("stateHistory", [])
        # State should be provided; subclasses define their own config-driven defaults
        state = data.get("state", "")
        if not state:
            raise ValueError("Entity state must be provided in data dict")
        return cls(
            id=data.get("id", ""),
            state=state,
            metadata=EntityMetadata.from_dict(data.get("metadata", {})),
            state_history=[StateHistoryEntry.from_dict(h) for h in history_data],
        )


__all__ = [
    "EntityId",
    "EntityMetadata",
    "StateHistoryEntry",
    "BaseEntity",
]


