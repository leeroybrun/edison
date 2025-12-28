"""Task planning utilities (parallelizable waves) derived from `depends_on`.

This module provides a topological "wave" plan for todo tasks so orchestrators
can run independent tasks in parallel without reading every task file.

Unlike `TaskReadinessEvaluator`, this planner does not treat dependencies that
are also todo tasks as "blocked" — it schedules them into later waves.
It only marks tasks as blocked when they depend on missing tasks or tasks that
are not in a configured satisfied state and are not part of the todo plan set.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from edison.core.task.index import TaskIndex, TaskSummary
from edison.core.task.readiness import BlockedByDependency, TaskReadinessEvaluator


@dataclass(frozen=True)
class TaskWave:
    wave: int
    tasks: tuple[TaskSummary, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave": self.wave,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title or "",
                    "state": t.state,
                }
                for t in self.tasks
            ],
        }


@dataclass(frozen=True)
class TaskPlan:
    waves: tuple[TaskWave, ...]
    blocked: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "waves": [w.to_dict() for w in self.waves],
            "blocked": list(self.blocked),
        }


def _blocked_task_payload(task: TaskSummary, blocked_by: Iterable[BlockedByDependency]) -> dict[str, Any]:
    blocked = [b.to_dict() for b in blocked_by]
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
        "id": task.id,
        "title": task.title or "",
        "state": task.state,
        "blockedBy": blocked,
        "unmetDependencies": unmet,
    }


class TaskPlanner:
    """Compute a topological wave plan for todo tasks."""

    def __init__(self, *, project_root: Path) -> None:
        self.project_root = project_root
        self._readiness = TaskReadinessEvaluator(project_root=project_root)

    def _order_wave_tasks(self, task_ids: list[str], tasks_by_id: Mapping[str, TaskSummary]) -> list[str]:
        """Order tasks within a wave, preferring related clusters.

        This is a best-effort heuristic and must remain deterministic.
        """
        ids = [str(t) for t in task_ids if t]
        if len(ids) <= 1:
            return ids

        universe = set(ids)

        parent: dict[str, str] = {tid: tid for tid in universe}

        def _find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def _union(a: str, b: str) -> None:
            ra, rb = _find(a), _find(b)
            if ra == rb:
                return
            # Deterministic union: attach larger-root lexicographically last to first.
            parent[max(ra, rb)] = min(ra, rb)

        # Build undirected edges across declared related IDs, but only within the wave set.
        for tid in universe:
            t = tasks_by_id.get(tid)
            if not t:
                continue
            related = getattr(t, "related", None) or []
            if not isinstance(related, list):
                continue
            for other in related:
                oid = str(other)
                if oid in universe:
                    _union(tid, oid)

        comps: dict[str, list[str]] = {}
        for tid in universe:
            root = _find(tid)
            comps.setdefault(root, []).append(tid)

        # Deterministic ordering: larger components first, then by smallest task id.
        clusters: list[list[str]] = []
        for comp in comps.values():
            clusters.append(sorted(comp))
        clusters.sort(key=lambda c: (-len(c), c[0]))

        out: list[str] = []
        for cluster in clusters:
            out.extend(cluster)
        return out

    def build_plan(self, *, session_id: Optional[str] = None) -> TaskPlan:
        graph = TaskIndex(project_root=self.project_root).get_task_graph(session_id=session_id)

        todo_state = self._readiness.todo_state()
        satisfied_states = self._readiness.dependency_satisfied_states()

        todo_tasks: dict[str, TaskSummary] = {
            tid: t for tid, t in graph.tasks.items() if t.state == todo_state
        }
        todo_ids = set(todo_tasks.keys())

        # Identify tasks blocked by dependencies outside the todo plan set.
        blocked_by: dict[str, list[BlockedByDependency]] = {}
        for tid, task in todo_tasks.items():
            for dep in task.depends_on or []:
                dep_id = str(dep)
                if dep_id in todo_ids:
                    continue
                dep_task = graph.tasks.get(dep_id)
                if dep_task is None:
                    blocked_by.setdefault(tid, []).append(
                        BlockedByDependency(
                            dependency_id=dep_id,
                            dependency_state=None,
                            required_states=satisfied_states,
                            reason="dependency task not found",
                        )
                    )
                    continue
                if dep_task.state not in satisfied_states:
                    blocked_by.setdefault(tid, []).append(
                        BlockedByDependency(
                            dependency_id=dep_task.id,
                            dependency_state=dep_task.state,
                            required_states=satisfied_states,
                            reason="dependency not in a satisfied state",
                        )
                    )

        # Propagate blockers: if you depend on a blocked todo task, you are also blocked
        # (because that upstream task cannot be scheduled until its external dependency is resolved).
        blocked_ids = set(blocked_by.keys())
        changed = True
        while changed:
            changed = False
            for tid, task in todo_tasks.items():
                if tid in blocked_ids:
                    continue
                for dep in task.depends_on or []:
                    dep_id = str(dep)
                    if dep_id in blocked_ids:
                        dep_state = todo_tasks.get(dep_id).state if dep_id in todo_tasks else None
                        blocked_by.setdefault(tid, []).append(
                            BlockedByDependency(
                                dependency_id=dep_id,
                                dependency_state=dep_state,
                                required_states=satisfied_states,
                                reason="dependency is externally blocked",
                            )
                        )
                        blocked_ids.add(tid)
                        changed = True
                        break

        eligible_ids = todo_ids - blocked_ids

        # Build adjacency (dependency -> dependents) within eligible tasks only.
        dependents: dict[str, set[str]] = {tid: set() for tid in eligible_ids}
        indegree: dict[str, int] = {tid: 0 for tid in eligible_ids}
        for tid in eligible_ids:
            task = todo_tasks[tid]
            for dep in task.depends_on or []:
                dep_id = str(dep)
                if dep_id not in eligible_ids:
                    continue
                dependents[dep_id].add(tid)
                indegree[tid] += 1

        waves: list[TaskWave] = []
        remaining = set(eligible_ids)
        wave_no = 1
        while remaining:
            ready = sorted([tid for tid in remaining if indegree.get(tid, 0) == 0])
            if not ready:
                # Cycle (or missing edges) inside eligible set. Fail-closed by emitting no further waves.
                break
            ordered_ids = self._order_wave_tasks(ready, todo_tasks)
            wave_tasks = tuple(todo_tasks[tid] for tid in ordered_ids)
            waves.append(TaskWave(wave=wave_no, tasks=wave_tasks))
            wave_no += 1
            for tid in ready:
                remaining.remove(tid)
                for child in dependents.get(tid, ()):
                    indegree[child] = max(0, indegree.get(child, 0) - 1)

        blocked_payloads = tuple(
            _blocked_task_payload(todo_tasks[tid], blocked_by.get(tid, [])) for tid in sorted(blocked_ids)
        )
        return TaskPlan(waves=tuple(waves), blocked=blocked_payloads)


__all__ = ["TaskPlanner", "TaskPlan", "TaskWave"]
