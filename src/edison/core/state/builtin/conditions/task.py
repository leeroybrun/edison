"""Task-specific condition functions for state machine transitions.

Conditions are predicates that check prerequisites for transitions.
They support OR logic for alternative conditions.
"""
from __future__ import annotations

from typing import Any, Mapping


def dependencies_satisfied(ctx: Mapping[str, Any]) -> bool:
    """Return True when the task's explicit dependencies are satisfied.

    This condition enforces `depends_on` ordering at claim/start time so that
    tasks cannot be claimed out-of-order.

    The satisfied states are configured in `tasks.readiness.dependencySatisfiedStates`
    and resolved through WorkflowConfig semantics.
    """
    # Optional escape hatch for exceptional situations (e.g., human-directed override).
    if bool(ctx.get("force")):
        return True

    task_id = ctx.get("task_id")
    if not task_id:
        task = ctx.get("task", {})
        if isinstance(task, Mapping):
            task_id = task.get("id") or task.get("task_id") or task.get("taskId")
    if not task_id:
        # If the caller didn't provide enough context, do not block unrelated transitions.
        return True

    try:
        from edison.core.task.readiness import TaskReadinessEvaluator
        from edison.core.utils.paths import PathResolver

        project_root = ctx.get("project_root") or PathResolver.resolve_project_root()
        evaluator = TaskReadinessEvaluator(project_root=project_root)
        return bool(evaluator.evaluate_task(str(task_id)).ready)
    except Exception:
        # FAIL-CLOSED for claim workflows: if we cannot evaluate dependencies, treat as blocked.
        return False


def has_task(ctx: Mapping[str, Any]) -> bool:
    """Check if session has at least one task.
    
    Args:
        ctx: Context with 'session' dict
        
    Returns:
        True if session has tasks
    """
    session = ctx.get("session", {})
    if not isinstance(session, Mapping):
        return True  # Allow if no session context
    
    # Check task count
    task_count = session.get("task_count")
    if task_count is not None:
        return int(task_count) > 0
    
    # Check tasks directly
    tasks = session.get("tasks")
    if isinstance(tasks, Mapping):
        return len(tasks) > 0
    if isinstance(tasks, list):
        return len(tasks) > 0
    
    # Empty session is allowed to activate (tasks claimed later)
    return True


def task_claimed(ctx: Mapping[str, Any]) -> bool:
    """Check if task is claimed by the session.
    
    Args:
        ctx: Context with 'session' or 'task' dict
        
    Returns:
        True if task is claimed
    """
    # Check session's claimed flag
    session = ctx.get("session", {})
    if isinstance(session, Mapping):
        claimed = session.get("claimed")
        if claimed is not None:
            return bool(claimed)
    
    # Check task's session_id
    task = ctx.get("task", {})
    if isinstance(task, Mapping):
        task_session = task.get("session_id") or task.get("sessionId")
        return bool(task_session)
    
    # Default to True for flexibility
    return True


def task_ready_for_qa(ctx: Mapping[str, Any]) -> bool:
    """Check if task is ready for QA validation.
    
    Args:
        ctx: Context with 'task' dict
        
    Returns:
        True if task is ready for QA
    """
    task = ctx.get("task", {})
    if not isinstance(task, Mapping):
        return False
    
    # Check ready flag
    ready = task.get("ready_for_qa") or task.get("ready_for_validation")
    if ready is not None:
        return bool(ready)
    
    # Check status - done tasks are ready for QA
    status = task.get("status", "")
    return str(status).lower() in ("done", "validated")


def no_task_graph_cycles(ctx: Mapping[str, Any]) -> bool:
    """Return True when the session task graph contains no cycles.

    This condition is used as a safety gate for task completion. Cycles can be
    introduced via parent/child links (parent_id) or dependency links
    (depends_on). A cyclic graph makes "blocking" semantics ambiguous and can
    deadlock promotion workflows.

    FAIL-CLOSED: If a session is present but tasks cannot be loaded, returns False.
    """
    session_id = ctx.get("session_id")
    if not session_id:
        session = ctx.get("session", {})
        if isinstance(session, Mapping):
            session_id = session.get("id")
    if not session_id:
        task = ctx.get("task", {})
        if isinstance(task, Mapping):
            session_id = task.get("session_id") or task.get("sessionId")

    # If the task is not session-scoped, skip the check.
    if not session_id:
        return True

    try:
        from edison.core.task.repository import TaskRepository
        from edison.core.utils.paths import PathResolver

        project_root = ctx.get("project_root")
        repo = TaskRepository(project_root=project_root or PathResolver.resolve_project_root())
        tasks = repo.find_by_session(str(session_id))
    except Exception:
        return False

    tasks_by_id = {t.id: t for t in tasks if getattr(t, "id", None)}
    if not tasks_by_id:
        return True

    graph: dict[str, set[str]] = {tid: set() for tid in tasks_by_id.keys()}
    for tid, t in tasks_by_id.items():
        parent_id = getattr(t, "parent_id", None)
        if parent_id and str(parent_id) in tasks_by_id:
            graph[tid].add(str(parent_id))
        depends_on = getattr(t, "depends_on", None) or []
        if isinstance(depends_on, list):
            for dep in depends_on:
                dep_id = str(dep)
                if dep_id in tasks_by_id:
                    graph[tid].add(dep_id)

    # Directed cycle detection (DFS with colors).
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in graph.keys()}

    for start in graph.keys():
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        stack: list[tuple[str, Any]] = [(start, iter(graph[start]))]
        while stack:
            node, it = stack[-1]
            try:
                nxt = next(it)
            except StopIteration:
                color[node] = BLACK
                stack.pop()
                continue

            nxt_color = color.get(nxt, WHITE)
            if nxt_color == WHITE:
                color[nxt] = GRAY
                stack.append((nxt, iter(graph.get(nxt, ()))) )
            elif nxt_color == GRAY:
                return False

    return True
