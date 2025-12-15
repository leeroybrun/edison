"""
Session domain models.

Data structures defined here provide a focused surface area for
session-related records. Includes the main Session entity and
supporting types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import (
    EntityMetadata,
    StateHistoryEntry,
)
from edison.core.entity.base import record_transition_impl
from edison.core.config.domains.session import SessionConfig


@dataclass
class SessionPaths:
    """Simple container for key session paths."""

    session_id: str
    path: Path
    status_dir: Path


@dataclass
class GitInfo:
    """Git-related information for a session."""
    
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    base_branch: str = "main"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "worktreePath": self.worktree_path,
            "branchName": self.branch_name,
            "baseBranch": self.base_branch,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitInfo":
        """Create from dict."""
        return cls(
            worktree_path=data.get("worktreePath"),
            branch_name=data.get("branchName"),
            base_branch=data.get("baseBranch", "main"),
        )


@dataclass
class Session:
    """A session entity representing a work session.
    
    Sessions track session-level data only. Task and QA data is stored
    in the task/QA files themselves (single source of truth).
    
    Use TaskIndex to query tasks/QA for this session:
        from edison.core.task import TaskIndex
        index = TaskIndex()
        tasks = index.list_tasks_in_session(session.id)
    
    Attributes:
        id: Unique session identifier
        state: Current session state
        phase: Current session phase
        owner: Session owner
        metadata: Entity metadata (timestamps, ownership)
        meta_extra: Additional arbitrary metadata (autoStarted, orchestratorProfile, etc.)
        state_history: List of state transitions
        git: Git-related information
        activity_log: List of activity log entries
        ready: Whether session is ready for work
    """
    id: str
    state: str
    phase: str = "implementation"
    owner: Optional[str] = None
    metadata: EntityMetadata = field(default_factory=lambda: EntityMetadata.create())
    meta_extra: Dict[str, Any] = field(default_factory=dict)  # For arbitrary metadata
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    git: GitInfo = field(default_factory=GitInfo)
    activity_log: List[Dict[str, Any]] = field(default_factory=list)
    ready: bool = True
    
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
        """
        record_transition_impl(
            self, from_state, to_state, reason=reason, violations=violations
        )
    
    def add_activity(self, message: str) -> None:
        """Add an activity log entry."""
        from edison.core.utils.time import utc_timestamp
        self.metadata.touch()
        self.activity_log.append({
            "timestamp": utc_timestamp(),
            "message": message,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Note: Task/QA data is NOT included - use TaskIndex to query tasks/QA.
        """
        # Build meta dict with core fields
        meta: Dict[str, Any] = {
            "sessionId": self.id,
            "owner": self.owner,
            "createdAt": self.metadata.created_at,
            "lastActive": self.metadata.updated_at,
            "status": self.state,
        }
        # Merge in any extra metadata (autoStarted, orchestratorProfile, etc.)
        meta.update(self.meta_extra)
        
        data: Dict[str, Any] = {
            "id": self.id,
            "state": self.state,
            "phase": self.phase,
            "meta": meta,
            "ready": self.ready,
        }
        
        data["git"] = self.git.to_dict()
        
        if self.activity_log:
            data["activityLog"] = self.activity_log
        
        if self.state_history:
            data["stateHistory"] = [h.to_dict() for h in self.state_history]
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create Session from dictionary representation.
        
        Note: `tasks` and `qa` fields in data are ignored - use TaskIndex for queries.
        """
        # Handle metadata
        meta = data.get("meta", {})
        metadata = EntityMetadata(
            created_at=meta.get("createdAt", ""),
            updated_at=meta.get("lastActive", ""),
            created_by=meta.get("owner"),
            session_id=data.get("id"),
        )
        
        # Extract extra metadata (fields not in core meta schema)
        core_meta_keys = {"sessionId", "owner", "createdAt", "lastActive", "status"}
        meta_extra = {k: v for k, v in meta.items() if k not in core_meta_keys}
        
        # Handle state history
        history_data = data.get("stateHistory", [])
        state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
        
        # Handle git info
        git_data = data.get("git", {})
        git = GitInfo.from_dict(git_data) if git_data else GitInfo()
        
        # Get state from data, fallback to config-driven initial state
        state = data.get("state") or SessionConfig().get_initial_session_state()
        
        return cls(
            id=data.get("id", ""),
            state=state,
            phase=data.get("phase", "implementation"),
            owner=meta.get("owner"),
            metadata=metadata,
            meta_extra=meta_extra,
            state_history=state_history,
            git=git,
            activity_log=data.get("activityLog", []),
            ready=data.get("ready", True),
        )
    
    @classmethod
    def create(
        cls,
        session_id: str,
        *,
        owner: Optional[str] = None,
        state: Optional[str] = None,
        phase: str = "implementation",
    ) -> "Session":
        """Factory method to create a new session."""
        # Resolve state from config if not provided
        resolved_state = state if state is not None else SessionConfig().get_initial_session_state()
        
        session = cls(
            id=session_id,
            state=resolved_state,
            phase=phase,
            owner=owner,
            metadata=EntityMetadata.create(
                created_by=owner,
                session_id=session_id,
            ),
        )
        session.add_activity("Session created")
        return session


__all__ = [
    "SessionPaths",
    "GitInfo",
    "Session",
]
