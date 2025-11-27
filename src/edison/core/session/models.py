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
    
    Sessions track the work being done, including tasks, QA records,
    git worktrees, and activity logs.
    
    Attributes:
        id: Unique session identifier
        state: Current session state
        phase: Current session phase
        owner: Session owner
        metadata: Entity metadata (timestamps, ownership)
        state_history: List of state transitions
        tasks: Dict of task entries keyed by task ID
        qa_records: Dict of QA entries keyed by QA ID
        git: Git-related information
        activity_log: List of activity log entries
    """
    id: str
    state: str
    phase: str = "implementation"
    owner: Optional[str] = None
    metadata: EntityMetadata = field(default_factory=lambda: EntityMetadata.create())
    state_history: List[StateHistoryEntry] = field(default_factory=list)
    tasks: Dict[str, TaskEntry] = field(default_factory=dict)
    qa_records: Dict[str, QAEntry] = field(default_factory=dict)
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
        """Record a state transition in history."""
        entry = StateHistoryEntry.create(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            violations=violations,
        )
        self.state_history.append(entry)
        self.metadata.touch()
    
    def add_activity(self, message: str) -> None:
        """Add an activity log entry."""
        from edison.core.utils.time import utc_timestamp
        self.activity_log.append({
            "timestamp": utc_timestamp(),
            "message": message,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data: Dict[str, Any] = {
            "id": self.id,
            "state": self.state,
            "phase": self.phase,
            "meta": {
                "sessionId": self.id,
                "owner": self.owner,
                "createdAt": self.metadata.created_at,
                "lastActive": self.metadata.updated_at,
                "status": self._state_to_status(self.state),
            },
            "ready": self.ready,
        }
        
        if self.tasks:
            data["tasks"] = {k: v.to_dict() for k, v in self.tasks.items()}
        else:
            data["tasks"] = {}
        
        if self.qa_records:
            data["qa"] = {k: v.to_dict() for k, v in self.qa_records.items()}
        else:
            data["qa"] = {}
        
        data["git"] = self.git.to_dict()
        
        if self.activity_log:
            data["activityLog"] = self.activity_log
        
        if self.state_history:
            data["stateHistory"] = [h.to_dict() for h in self.state_history]
        
        return data
    
    def _state_to_status(self, state: str) -> str:
        """Map state to legacy status field."""
        mapping = {
            "active": "wip",
            "wip": "wip",
            "done": "done",
            "validated": "validated",
            "closing": "done",
        }
        return mapping.get(state, state)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create Session from dictionary representation."""
        # Handle metadata
        meta = data.get("meta", {})
        metadata = EntityMetadata(
            created_at=meta.get("createdAt", ""),
            updated_at=meta.get("lastActive", ""),
            created_by=meta.get("owner"),
            session_id=data.get("id"),
        )
        
        # Handle state history
        history_data = data.get("stateHistory", [])
        state_history = [StateHistoryEntry.from_dict(h) for h in history_data]
        
        # Handle tasks
        tasks_data = data.get("tasks", {})
        tasks = {}
        for tid, tdata in tasks_data.items():
            if isinstance(tdata, dict):
                tasks[tid] = TaskEntry(
                    record_id=tdata.get("recordId", tid),
                    status=tdata.get("status", ""),
                    owner=tdata.get("owner", ""),
                    qa_id=tdata.get("qaId"),
                    parent_id=tdata.get("parentId"),
                    child_ids=tdata.get("childIds", []),
                    claimed_at=tdata.get("claimedAt"),
                    last_active=tdata.get("lastActive"),
                    automation=tdata.get("automation", {}),
                    notes=tdata.get("notes", []),
                )
        
        # Handle QA records
        qa_data = data.get("qa", {})
        qa_records = {}
        for qid, qdata in qa_data.items():
            if isinstance(qdata, dict):
                qa_records[qid] = QAEntry(
                    record_id=qdata.get("recordId", qid),
                    task_id=qdata.get("taskId", ""),
                    status=qdata.get("status", ""),
                    round=qdata.get("round", 1),
                    evidence=qdata.get("evidence", []),
                    validators=qdata.get("validators", []),
                )
        
        # Handle git info
        git_data = data.get("git", {})
        git = GitInfo.from_dict(git_data) if git_data else GitInfo()
        
        return cls(
            id=data.get("id", ""),
            state=data.get("state", "active"),
            phase=data.get("phase", "implementation"),
            owner=meta.get("owner"),
            metadata=metadata,
            state_history=state_history,
            tasks=tasks,
            qa_records=qa_records,
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
        state: str = "active",
        phase: str = "implementation",
    ) -> "Session":
        """Factory method to create a new session."""
        session = cls(
            id=session_id,
            state=state,
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
    "TaskEntry",
    "QAEntry",
    "GitInfo",
    "Session",
]

