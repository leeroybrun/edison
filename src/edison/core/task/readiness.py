"""Derived task readiness/blocked semantics computed from the task graph.

Edison tasks have explicit graph metadata (depends_on, parent_id, child_ids).
This module derives:
- ready: task is in semantic "todo" and all dependencies are satisfied
- blocked: task is in semantic "todo" but has unmet dependencies (with "why")

These semantics are computed from the graph (frontmatter), not just a static
"todo/wip/done" state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from edison.core.config.domains.task import TaskConfig
from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.task.index import TaskGraph, TaskIndex, TaskSummary


@dataclass(frozen=True)
class BlockedByDependency:
    dependency_id: str
    dependency_state: Optional[str]
    required_states: tuple[str, ...]
    reason: str
    dependency_session_id: Optional[str] = None
    dependency_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependencyId": self.dependency_id,
            "dependencyState": self.dependency_state,
            "requiredStates": list(self.required_states),
            "reason": self.reason,
            "dependencySessionId": self.dependency_session_id,
            "dependencyPath": self.dependency_path,
        }


@dataclass(frozen=True)
class TaskReadiness:
    task: TaskSummary
    ready: bool
    blocked_by: tuple[BlockedByDependency, ...] = ()

    def to_ready_list_dict(self) -> dict[str, Any]:
        return {
            "id": self.task.id,
            "title": self.task.title or "",
            "state": self.task.state,
        }

    def to_blocked_list_dict(self) -> dict[str, Any]:
        blocked = [b.to_dict() for b in self.blocked_by]
        unmet = [
            {
                "id": b.get("dependencyId"),
                "state": b.get("dependencyState"),
                "requiredStates": b.get("requiredStates", []),
                "reason": b.get("reason", ""),
            }
            for b in blocked
        ]
        return {
            "id": self.task.id,
            "title": self.task.title or "",
            "state": self.task.state,
            # Primary key (current)
            "blockedBy": blocked,
            # Compatibility alias (more explicit for consumers)
            "unmetDependencies": unmet,
        }

    def to_blocked_detail_dict(self, *, todo_state: str) -> dict[str, Any]:
        """Return a detailed blocked/readiness payload for a single task."""
        payload = self.to_blocked_list_dict()
        payload.update(
            {
                # `ready` means "ready to claim" (only meaningful for todo tasks).
                "ready": self.ready,
                # `blocked` is the dependency-blocked signal (todo + unmet deps).
                "blocked": bool(self.blocked_by),
                "todoState": todo_state,
            }
        )
        return payload


class TaskReadinessEvaluator:
    """Compute readiness/blocked semantics from the task graph."""

    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root
        self._workflow = WorkflowConfig(repo_root=project_root)
        self._tasks_cfg = TaskConfig(repo_root=project_root)

    def todo_state(self) -> str:
        """Return the resolved task semantic 'todo' state string."""
        return str(self._workflow.get_semantic_state("task", "todo"))

    def dependency_satisfied_states(self) -> tuple[str, ...]:
        """Return resolved task states that satisfy `depends_on` prerequisites."""
        cfg = self._tasks_cfg.section.get("readiness", {}) or {}
        raw = cfg.get("dependencySatisfiedStates", [])  # semantic state keys
        if not isinstance(raw, list) or not raw:
            raise ValueError("Missing configuration: tasks.readiness.dependencySatisfiedStates")
        resolved: list[str] = []
        for semantic in raw:
            try:
                resolved.append(str(self._workflow.get_semantic_state("task", str(semantic))))
            except Exception:
                # Fail-open for unknown semantics; ignore.
                continue
        return tuple(resolved)

    def treat_missing_dependency_as_blocked(self) -> bool:
        """Return True if missing dependency IDs should block readiness."""
        cfg = self._tasks_cfg.section.get("readiness", {}) or {}
        val = cfg.get("treatMissingDependencyAsBlocked")
        return True if val is None else bool(val)

    def _full_graph(self) -> TaskGraph:
        """Return full graph including all session tasks (for diagnostics)."""
        return TaskIndex(project_root=self.project_root).get_task_graph(
            session_id=None,
            include_session_tasks=True,
        )

    def _scoped_graph(self, *, full: TaskGraph, session_id: Optional[str]) -> TaskGraph:
        """Return a graph view scoped to global + (optional) one session.

        Invariants:
        - When session_id is None: ONLY global tasks participate.
        - When session_id is set: global tasks + tasks in that session participate.
        - Tasks from other sessions never satisfy dependencies.
        """
        if session_id is None:
            tasks = {tid: t for tid, t in full.tasks.items() if t.session_id is None}
        else:
            sid = str(session_id)
            tasks = {tid: t for tid, t in full.tasks.items() if t.session_id is None or t.session_id == sid}
        return TaskGraph(tasks=tasks)

    def evaluate_task(self, task_id: str, *, session_id: Optional[str] = None) -> TaskReadiness:
        full = self._full_graph()
        task = full.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        scope_session_id = task.session_id if session_id is None else str(session_id)
        scoped = self._scoped_graph(full=full, session_id=scope_session_id)
        scoped_task = scoped.tasks.get(task_id)
        if scoped_task is None:
            # If task is session-scoped but missing session_id metadata, fall back to full.
            scoped_task = task
        return self._evaluate_summary(scoped_task, scoped, full)

    def list_ready_tasks(self, *, session_id: Optional[str] = None) -> list[TaskReadiness]:
        full = self._full_graph()
        graph = self._scoped_graph(full=full, session_id=session_id)
        todo_state = self.todo_state()
        out: list[TaskReadiness] = []
        for t in graph.tasks.values():
            if t.state != todo_state:
                continue
            if session_id is not None and t.session_id != session_id:
                continue
            r = self._evaluate_summary(t, graph, full)
            if r.ready:
                out.append(r)
        out.sort(key=lambda r: r.task.id)
        return out

    def list_blocked_tasks(self, *, session_id: Optional[str] = None) -> list[TaskReadiness]:
        full = self._full_graph()
        graph = self._scoped_graph(full=full, session_id=session_id)
        todo_state = self.todo_state()
        out: list[TaskReadiness] = []
        for t in graph.tasks.values():
            if t.state != todo_state:
                continue
            if session_id is not None and t.session_id != session_id:
                continue
            r = self._evaluate_summary(t, graph, full)
            if not r.ready and r.blocked_by:
                out.append(r)
        out.sort(key=lambda r: r.task.id)
        return out

    def _evaluate_summary(self, task: TaskSummary, graph: TaskGraph, full: TaskGraph) -> TaskReadiness:
        todo_state = self.todo_state()
        if task.state != todo_state:
            return TaskReadiness(task=task, ready=False, blocked_by=())

        satisfied_states = self.dependency_satisfied_states()
        blocked: list[BlockedByDependency] = []

        for dep_id in task.depends_on or []:
            dep_id_str = str(dep_id)
            dep = graph.tasks.get(dep_id_str)
            if dep is None:
                if self.treat_missing_dependency_as_blocked():
                    found_any = full.tasks.get(dep_id_str)
                    if found_any is not None and found_any.session_id is not None:
                        blocked.append(
                            BlockedByDependency(
                                dependency_id=dep_id_str,
                                dependency_state=found_any.state,
                                required_states=satisfied_states,
                                reason=f"dependency exists in another session ({found_any.session_id})",
                                dependency_session_id=found_any.session_id,
                                dependency_path=str(found_any.path),
                            )
                        )
                        continue
                    blocked.append(
                        BlockedByDependency(
                            dependency_id=dep_id_str,
                            dependency_state=None,
                            required_states=satisfied_states,
                            reason="dependency task not found",
                        )
                    )
                continue

            if dep.state not in satisfied_states:
                blocked.append(
                    BlockedByDependency(
                        dependency_id=dep.id,
                        dependency_state=dep.state,
                        required_states=satisfied_states,
                        reason="dependency not in a satisfied state",
                        dependency_session_id=dep.session_id,
                        dependency_path=str(dep.path),
                    )
                )

        return TaskReadiness(task=task, ready=(len(blocked) == 0), blocked_by=tuple(blocked))


__all__ = [
    "BlockedByDependency",
    "TaskReadiness",
    "TaskReadinessEvaluator",
]
