"""Task entity models.

This module defines the Task dataclass and related types for the task
domain. Tasks represent units of work that can be created, claimed,
and transitioned through various states.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    EntityMetadata,
    StateHistoryEntry,
)


@dataclass
class Task:
    """A task entity representing a unit of work.
    
    Tasks flow through states: todo -> wip -> done -> validated
    
    Attributes:
        id: Unique task identifier (e.g., "T-001")
        state: Current task state
        title: Task title/summary
        description: Detailed task description
        session_id: Associated session identifier (optional)
        metadata: Entity metadata (timestamps, ownership)
        state_history: List of state transitions
        tags: Optional list of tags
        parent_id: Parent task ID for subtasks (optional)
        children: List of child task IDs
        result: Task result/outcome (optional)
    """
    id: str
    state: str
    title: str
    description: str = ""
    session_id: Optional[str] = None
    metadata: EntityMetadata = field(default_factory=lambda: EntityMetadata.create())
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    result: Optional[str] = None
    
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
        
        Returns:
            Dict with task data in JSON-compatible format
        """
        data: Dict[str, Any] = {
            "id": self.id,
            "state": self.state,
            "title": self.title,
        }
        
        if self.description:
            data["description"] = self.description
        
        if self.session_id:
            data["sessionId"] = self.session_id
        
        data["metadata"] = self.metadata.to_dict()
        
        if self.state_history:
            data["stateHistory"] = [h.to_dict() for h in self.state_history]
        
        if self.tags:
            data["tags"] = self.tags
        
        if self.parent_id:
            data["parentId"] = self.parent_id
        
        if self.children:
            data["children"] = self.children
        
        if self.result:
            data["result"] = self.result
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary representation.
        
        Args:
            data: Dict with task data
            
        Returns:
            Task instance
        """
        # Handle metadata
        metadata_data = data.get("metadata", {})
        if not metadata_data:
            # Build metadata from legacy fields if present
            metadata_data = {
                "createdAt": data.get("createdAt") or data.get("created_at"),
                "updatedAt": data.get("updatedAt") or data.get("updated_at"),
                "createdBy": data.get("owner") or data.get("createdBy"),
                "sessionId": data.get("sessionId") or data.get("session_id"),
            }
        metadata = EntityMetadata.from_dict(metadata_data)
        
        # Handle state history
        history_data = data.get("stateHistory", [])
        state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
        
        return cls(
            id=data.get("id", ""),
            state=data.get("state") or data.get("status") or "todo",
            title=data.get("title", ""),
            description=data.get("description", ""),
            session_id=data.get("sessionId") or data.get("session_id"),
            metadata=metadata,
            state_history=state_history,
            tags=data.get("tags", []),
            parent_id=data.get("parentId") or data.get("parent_id"),
            children=data.get("children", []),
            result=data.get("result"),
        )
    
    @classmethod
    def create(
        cls,
        task_id: str,
        title: str,
        *,
        description: str = "",
        session_id: Optional[str] = None,
        owner: Optional[str] = None,
        state: str = "todo",
    ) -> "Task":
        """Factory method to create a new task.
        
        Args:
            task_id: Task identifier
            title: Task title
            description: Task description
            session_id: Associated session
            owner: Task owner/creator
            state: Initial state (default: todo)
            
        Returns:
            New Task instance
        """
        return cls(
            id=task_id,
            state=state,
            title=title,
            description=description,
            session_id=session_id,
            metadata=EntityMetadata.create(
                created_by=owner,
                session_id=session_id,
            ),
        )


__all__ = [
    "Task",
]


