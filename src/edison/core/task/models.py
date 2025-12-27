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
from edison.core.entity.base import record_transition_impl
from edison.core.config.domains.workflow import WorkflowConfig


@dataclass
class Task:
    """A task entity representing a unit of work.
    
    Tasks flow through states: todo -> wip -> done -> validated
    State is derived from directory location, NOT stored in the model.
    
    Attributes:
        id: Unique task identifier (e.g., "task-150-auth-gate")
        state: Current task state (derived from directory location)
        title: Task title/summary
        description: Detailed task description
        session_id: Associated session identifier (optional)
        metadata: Entity metadata (timestamps, ownership)
        state_history: List of state transitions
        tags: Optional list of tags
        parent_id: Parent task ID for subtasks (optional)
        child_ids: List of child task IDs
        depends_on: List of task IDs this task depends on
        blocks_tasks: List of task IDs blocked by this task
        claimed_at: ISO timestamp when task was claimed by a session
        last_active: ISO timestamp of last activity
        continuation_id: Pal MCP continuation ID for tracking
        result: Task result/outcome (optional)
        delegated_to: Who the task was delegated to (optional)
        delegated_in_session: Session ID where delegation happened (optional)
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
    child_ids: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    blocks_tasks: List[str] = field(default_factory=list)
    claimed_at: Optional[str] = None
    last_active: Optional[str] = None
    continuation_id: Optional[str] = None
    result: Optional[str] = None
    delegated_to: Optional[str] = None
    delegated_in_session: Optional[str] = None
    
    def record_transition(
        self,
        from_state: str,
        to_state: str,
        *,
        reason: Optional[str] = None,
        violations: Optional[List[str]] = None,
    ) -> None:
        """Record a state transition in history.
        
        Delegates to shared record_transition_impl for DRY compliance.
        
        Args:
            from_state: Previous state
            to_state: New state
            reason: Optional reason for transition
            violations: Optional list of rule violations
        """
        record_transition_impl(
            self, from_state, to_state, reason=reason, violations=violations
        )
    
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
            data["session_id"] = self.session_id
        
        data["metadata"] = self.metadata.to_dict()
        
        if self.state_history:
            data["state_history"] = [h.to_dict() for h in self.state_history]
        
        if self.tags:
            data["tags"] = self.tags
        
        if self.parent_id:
            data["parent_id"] = self.parent_id
        
        if self.child_ids:
            data["child_ids"] = self.child_ids
        
        if self.depends_on:
            data["depends_on"] = self.depends_on
        
        if self.blocks_tasks:
            data["blocks_tasks"] = self.blocks_tasks
        
        if self.claimed_at:
            data["claimed_at"] = self.claimed_at
        
        if self.last_active:
            data["last_active"] = self.last_active
        
        if self.continuation_id:
            data["continuation_id"] = self.continuation_id
        
        if self.result:
            data["result"] = self.result

        if self.delegated_to:
            data["delegated_to"] = self.delegated_to
        if self.delegated_in_session:
            data["delegated_in_session"] = self.delegated_in_session
        
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
        
        # Handle state history (support both snake_case and camelCase)
        history_data = data.get("state_history") or data.get("stateHistory", [])
        state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
        
        # Get state from data, fallback to config-driven initial state
        state = data.get("state") or data.get("status") or WorkflowConfig().get_initial_state("task")
        
        return cls(
            id=data.get("id", ""),
            state=state,
            title=data.get("title", ""),
            description=data.get("description", ""),
            session_id=data.get("session_id") or data.get("sessionId"),
            metadata=metadata,
            state_history=state_history,
            tags=data.get("tags", []),
            parent_id=data.get("parent_id") or data.get("parentId"),
            child_ids=data.get("child_ids") or data.get("childIds") or data.get("children", []),
            depends_on=data.get("depends_on") or data.get("dependsOn", []),
            blocks_tasks=data.get("blocks_tasks") or data.get("blocksTasks", []),
            claimed_at=data.get("claimed_at") or data.get("claimedAt"),
            last_active=data.get("last_active") or data.get("lastActive"),
            continuation_id=data.get("continuation_id") or data.get("continuationId"),
            result=data.get("result"),
            delegated_to=data.get("delegated_to") or data.get("delegatedTo"),
            delegated_in_session=data.get("delegated_in_session") or data.get("delegatedInSession"),
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
        state: Optional[str] = None,
        parent_id: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        blocks_tasks: Optional[List[str]] = None,
        continuation_id: Optional[str] = None,
    ) -> "Task":
        """Factory method to create a new task.
        
        Args:
            task_id: Task identifier
            title: Task title
            description: Task description
            session_id: Associated session
            owner: Task owner/creator
            state: Initial state (default: from config)
            parent_id: Parent task ID for subtasks
            depends_on: List of task IDs this task depends on
            blocks_tasks: List of task IDs blocked by this task
            continuation_id: Pal MCP continuation ID
            
        Returns:
            New Task instance
        """
        # Resolve state from config if not provided
        resolved_state = state if state is not None else WorkflowConfig().get_initial_state("task")
        
        return cls(
            id=task_id,
            state=resolved_state,
            title=title,
            description=description,
            session_id=session_id,
            metadata=EntityMetadata.create(
                created_by=owner,
                session_id=session_id,
            ),
            parent_id=parent_id,
            depends_on=depends_on or [],
            blocks_tasks=blocks_tasks or [],
            continuation_id=continuation_id,
        )


__all__ = [
    "Task",
]


