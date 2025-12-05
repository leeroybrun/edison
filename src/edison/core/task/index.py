"""Task indexing service for fast task/QA discovery.

This module provides a TaskIndex service that uses file system operations
to discover and index tasks/QA records. This replaces the need for session JSON
to store task/QA entries.

The index can:
1. List all tasks/QA in a session by scanning frontmatter
2. Build task dependency graphs from frontmatter metadata
3. Find tasks by various criteria (session_id, state, parent_id, etc.)
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.utils.paths import PathResolver
from edison.core.utils.text import parse_frontmatter, has_frontmatter
from edison.core.config.domains import TaskConfig


@dataclass
class TaskSummary:
    """Lightweight task summary from frontmatter.
    
    Used for building indexes without loading full Task entities.
    """
    id: str
    path: Path
    state: str  # Derived from directory
    session_id: Optional[str] = None
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    blocks_tasks: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    title: Optional[str] = None


@dataclass
class QASummary:
    """Lightweight QA summary from frontmatter.
    
    Used for building indexes without loading full QARecord entities.
    """
    id: str
    path: Path
    state: str  # Derived from directory
    task_id: str
    session_id: Optional[str] = None
    round: int = 1
    validator_owner: Optional[str] = None
    title: Optional[str] = None


@dataclass
class TaskGraph:
    """Graph of task relationships.
    
    Represents parent/child and dependency relationships between tasks.
    """
    tasks: Dict[str, TaskSummary] = field(default_factory=dict)
    parent_children: Dict[str, List[str]] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> depends_on
    blockers: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> blocks_tasks
    
    def get_children(self, task_id: str) -> List[str]:
        """Get direct children of a task."""
        return self.parent_children.get(task_id, [])
    
    def get_dependencies(self, task_id: str) -> List[str]:
        """Get tasks that must complete before this task."""
        return self.dependencies.get(task_id, [])
    
    def get_blocked_by(self, task_id: str) -> List[str]:
        """Get tasks that are blocked by this task."""
        return self.blockers.get(task_id, [])
    
    def get_all_ancestors(self, task_id: str) -> Set[str]:
        """Get all ancestor task IDs (recursive parents)."""
        ancestors: Set[str] = set()
        task = self.tasks.get(task_id)
        if task and task.parent_id:
            ancestors.add(task.parent_id)
            ancestors.update(self.get_all_ancestors(task.parent_id))
        return ancestors
    
    def get_all_descendants(self, task_id: str) -> Set[str]:
        """Get all descendant task IDs (recursive children)."""
        descendants: Set[str] = set()
        for child_id in self.get_children(task_id):
            descendants.add(child_id)
            descendants.update(self.get_all_descendants(child_id))
        return descendants


class TaskIndex:
    """Service for indexing and discovering tasks/QA records.
    
    This service provides fast discovery of tasks and QA records by scanning
    the file system. It replaces the session JSON for task/QA tracking.
    
    Usage:
        index = TaskIndex(project_root)
        
        # Find all tasks in a session
        tasks = index.list_tasks_in_session("python-pid-123")
        
        # Build task dependency graph
        graph = index.get_task_graph()
        
        # Find tasks by state
        wip_tasks = index.find_tasks_by_state("wip")
    """
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize the task index.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = TaskConfig(repo_root=self.project_root)
        
    def _get_tasks_root(self) -> Path:
        """Get the global tasks root directory."""
        return self._config.tasks_root()
    
    def _get_qa_root(self) -> Path:
        """Get the global QA root directory."""
        return self._config.qa_root()
    
    def _get_sessions_root(self) -> Path:
        """Get the sessions root directory."""
        return self.project_root / ".project" / "sessions"
    
    # ---------- Task Discovery ----------
    
    def scan_all_task_files(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """Scan all task files and extract frontmatter.
        
        Returns:
            List of (path, frontmatter_dict) tuples
        """
        results: List[Tuple[Path, Dict[str, Any]]] = []
        
        # Scan global tasks
        tasks_root = self._get_tasks_root()
        if tasks_root.exists():
            for md_file in tasks_root.rglob("*.md"):
                if md_file.name == "TEMPLATE.md":
                    continue
                fm = self._extract_frontmatter(md_file)
                if fm is not None:
                    results.append((md_file, fm))
        
        # Scan session tasks
        sessions_root = self._get_sessions_root()
        if sessions_root.exists():
            for session_dir in sessions_root.rglob("tasks"):
                if session_dir.is_dir():
                    for md_file in session_dir.rglob("*.md"):
                        fm = self._extract_frontmatter(md_file)
                        if fm is not None:
                            results.append((md_file, fm))
        
        return results
    
    def scan_all_qa_files(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """Scan all QA files and extract frontmatter.
        
        Returns:
            List of (path, frontmatter_dict) tuples
        """
        results: List[Tuple[Path, Dict[str, Any]]] = []
        
        # Scan global QA
        qa_root = self._get_qa_root()
        if qa_root.exists():
            for md_file in qa_root.rglob("*.md"):
                if md_file.name == "TEMPLATE.md":
                    continue
                fm = self._extract_frontmatter(md_file)
                if fm is not None:
                    results.append((md_file, fm))
        
        # Scan session QA
        sessions_root = self._get_sessions_root()
        if sessions_root.exists():
            for qa_dir in sessions_root.rglob("qa"):
                if qa_dir.is_dir() and qa_dir.name == "qa":
                    for md_file in qa_dir.rglob("*.md"):
                        fm = self._extract_frontmatter(md_file)
                        if fm is not None:
                            results.append((md_file, fm))
        
        return results
    
    def _extract_frontmatter(self, path: Path) -> Optional[Dict[str, Any]]:
        """Extract frontmatter from a markdown file.
        
        Args:
            path: Path to markdown file
            
        Returns:
            Frontmatter dict or None if parsing failed
        """
        try:
            content = path.read_text(encoding="utf-8")
            if has_frontmatter(content):
                doc = parse_frontmatter(content)
                return doc.frontmatter
            return {}
        except Exception:
            return None
    
    # ---------- Task Queries ----------
    
    def list_tasks_in_session(self, session_id: str) -> List[TaskSummary]:
        """Find all tasks belonging to a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of TaskSummary objects
        """
        results: List[TaskSummary] = []
        
        for path, fm in self.scan_all_task_files():
            if fm.get("session_id") == session_id:
                state = path.parent.name
                results.append(TaskSummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    session_id=session_id,
                    parent_id=fm.get("parent_id"),
                    child_ids=fm.get("child_ids", []) or [],
                    depends_on=fm.get("depends_on", []) or [],
                    blocks_tasks=fm.get("blocks_tasks", []) or [],
                    owner=fm.get("owner"),
                    title=fm.get("title"),
                ))
        
        return results
    
    def list_qa_in_session(self, session_id: str) -> List[QASummary]:
        """Find all QA records belonging to a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of QASummary objects
        """
        results: List[QASummary] = []
        
        for path, fm in self.scan_all_qa_files():
            if fm.get("session_id") == session_id:
                state = path.parent.name
                results.append(QASummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    task_id=fm.get("task_id", ""),
                    session_id=session_id,
                    round=fm.get("round", 1),
                    validator_owner=fm.get("validator_owner"),
                    title=fm.get("title"),
                ))
        
        return results
    
    def find_tasks_by_state(self, state: str) -> List[TaskSummary]:
        """Find all tasks in a given state.
        
        Args:
            state: Task state (todo, wip, done, etc.)
            
        Returns:
            List of TaskSummary objects
        """
        results: List[TaskSummary] = []
        
        for path, fm in self.scan_all_task_files():
            if path.parent.name == state:
                results.append(TaskSummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    session_id=fm.get("session_id"),
                    parent_id=fm.get("parent_id"),
                    child_ids=fm.get("child_ids", []) or [],
                    depends_on=fm.get("depends_on", []) or [],
                    blocks_tasks=fm.get("blocks_tasks", []) or [],
                    owner=fm.get("owner"),
                    title=fm.get("title"),
                ))
        
        return results
    
    def find_qa_by_state(self, state: str) -> List[QASummary]:
        """Find all QA records in a given state.
        
        Args:
            state: QA state (waiting, todo, wip, done, etc.)
            
        Returns:
            List of QASummary objects
        """
        results: List[QASummary] = []
        
        for path, fm in self.scan_all_qa_files():
            if path.parent.name == state:
                results.append(QASummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    task_id=fm.get("task_id", ""),
                    session_id=fm.get("session_id"),
                    round=fm.get("round", 1),
                    validator_owner=fm.get("validator_owner"),
                    title=fm.get("title"),
                ))
        
        return results
    
    def find_qa_for_task(self, task_id: str) -> List[QASummary]:
        """Find all QA records for a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of QASummary objects
        """
        results: List[QASummary] = []
        
        for path, fm in self.scan_all_qa_files():
            if fm.get("task_id") == task_id:
                state = path.parent.name
                results.append(QASummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    task_id=task_id,
                    session_id=fm.get("session_id"),
                    round=fm.get("round", 1),
                    validator_owner=fm.get("validator_owner"),
                    title=fm.get("title"),
                ))
        
        return results
    
    # ---------- Task Graph ----------
    
    def get_task_graph(self, session_id: Optional[str] = None) -> TaskGraph:
        """Build a task dependency graph.
        
        Args:
            session_id: Optional session to filter by
            
        Returns:
            TaskGraph with all task relationships
        """
        graph = TaskGraph()
        
        for path, fm in self.scan_all_task_files():
            # Filter by session if specified
            if session_id and fm.get("session_id") != session_id:
                continue
            
            state = path.parent.name
            task_id = fm.get("id", path.stem)
            
            summary = TaskSummary(
                id=task_id,
                path=path,
                state=state,
                session_id=fm.get("session_id"),
                parent_id=fm.get("parent_id"),
                child_ids=fm.get("child_ids", []) or [],
                depends_on=fm.get("depends_on", []) or [],
                blocks_tasks=fm.get("blocks_tasks", []) or [],
                owner=fm.get("owner"),
                title=fm.get("title"),
            )
            
            graph.tasks[task_id] = summary
            
            # Build parent->children mapping
            if summary.parent_id:
                if summary.parent_id not in graph.parent_children:
                    graph.parent_children[summary.parent_id] = []
                if task_id not in graph.parent_children[summary.parent_id]:
                    graph.parent_children[summary.parent_id].append(task_id)
            
            # Build dependencies
            if summary.depends_on:
                graph.dependencies[task_id] = summary.depends_on
            
            # Build blockers
            if summary.blocks_tasks:
                graph.blockers[task_id] = summary.blocks_tasks
        
        return graph
    
    def find_unclaimed_tasks(self) -> List[TaskSummary]:
        """Find all tasks that are not claimed by any session.
        
        Returns:
            List of TaskSummary objects for unclaimed tasks
        """
        results: List[TaskSummary] = []
        
        for path, fm in self.scan_all_task_files():
            if not fm.get("session_id"):
                state = path.parent.name
                results.append(TaskSummary(
                    id=fm.get("id", path.stem),
                    path=path,
                    state=state,
                    session_id=None,
                    parent_id=fm.get("parent_id"),
                    child_ids=fm.get("child_ids", []) or [],
                    depends_on=fm.get("depends_on", []) or [],
                    blocks_tasks=fm.get("blocks_tasks", []) or [],
                    owner=fm.get("owner"),
                    title=fm.get("title"),
                ))
        
        return results


__all__ = [
    "TaskIndex",
    "TaskSummary",
    "QASummary",
    "TaskGraph",
]


