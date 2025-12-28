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

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependencyId": self.dependency_id,
            "dependencyState": self.dependency_state,
            "requiredStates": list(self.required_states),
            "reason": self.reason,
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

    def _graph(self) -> TaskGraph:
        return TaskIndex(project_root=self.project_root).get_task_graph(session_id=None)

    def evaluate_task(self, task_id: str) -> TaskReadiness:
        graph = self._graph()
        task = graph.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return self._evaluate_summary(task, graph)

    def list_ready_tasks(self, *, session_id: Optional[str] = None) -> list[TaskReadiness]:
        graph = self._graph()
        todo_state = self.todo_state()
        out: list[TaskReadiness] = []
        for t in graph.tasks.values():
            if t.state != todo_state:
                continue
            if session_id is not None and t.session_id != session_id:
                continue
            r = self._evaluate_summary(t, graph)
            if r.ready:
                out.append(r)
        out.sort(key=lambda r: r.task.id)
        return out

    def list_blocked_tasks(self, *, session_id: Optional[str] = None) -> list[TaskReadiness]:
        graph = self._graph()
        todo_state = self.todo_state()
        out: list[TaskReadiness] = []
        for t in graph.tasks.values():
            if t.state != todo_state:
                continue
            if session_id is not None and t.session_id != session_id:
                continue
            r = self._evaluate_summary(t, graph)
            if not r.ready and r.blocked_by:
                out.append(r)
        out.sort(key=lambda r: r.task.id)
        return out

    def _evaluate_summary(self, task: TaskSummary, graph: TaskGraph) -> TaskReadiness:
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
                    )
                )

        return TaskReadiness(task=task, ready=(len(blocked) == 0), blocked_by=tuple(blocked))


__all__ = [
    "BlockedByDependency",
    "TaskReadiness",
    "TaskReadinessEvaluator",
]
