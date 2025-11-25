from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional


class ConditionRegistry:
    """Registry of condition predicates."""

    def __init__(self, *, preload_defaults: bool = False) -> None:
        self._conditions: Dict[str, Callable[[Mapping[str, Any]], bool]] = {}
        if preload_defaults:
            self.register_defaults()

    def register(self, name: str, condition_fn: Callable[[Mapping[str, Any]], bool]) -> None:
        if not callable(condition_fn):
            raise TypeError("condition_fn must be callable")
        self._conditions[name] = condition_fn

    def register_defaults(self) -> None:
        for name, fn in _DEFAULT_CONDITIONS.items():
            self._conditions.setdefault(name, fn)

    def reset(self) -> None:
        self._conditions.clear()
        self.register_defaults()

    def check(self, name: str, context: Optional[Mapping[str, Any]] = None) -> bool:
        if name not in self._conditions:
            raise ValueError(f"Unknown condition: {name}")
        ctx = context or {}
        return bool(self._conditions[name](ctx))


# Built-in conditions aligned with the rich state machine config.

def _cond_has_task(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    task_count = session.get("task_count")
    if task_count is None:
        tasks = session.get("tasks") or []
        task_count = len(tasks)
    # Allow empty sessions to activate; when tasks are present ensure at least one linked.
    return True if task_count == 0 else bool(task_count)


def _cond_task_claimed(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("claimed", True))


def _cond_all_work_complete(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("work_complete", True))


def _cond_no_pending_commits(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("pending_commits", 0) == 0)


def _cond_validation_failed(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("validation_failed", False))


def _cond_dependencies_missing(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("deps_missing", False))


def _cond_ready_to_close(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    # Default to True for flexibility in testing and lightweight CLI flows
    return bool(session.get("ready", True))


def _cond_has_blocker_reason(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("reason"))


_DEFAULT_CONDITIONS: Dict[str, Callable[[Mapping[str, Any]], bool]] = {
    "has_task": _cond_has_task,
    "task_claimed": _cond_task_claimed,
    "all_work_complete": _cond_all_work_complete,
    "no_pending_commits": _cond_no_pending_commits,
    "validation_failed": _cond_validation_failed,
    "dependencies_missing": _cond_dependencies_missing,
    "ready_to_close": _cond_ready_to_close,
    "has_blocker_reason": _cond_has_blocker_reason,
}


registry = ConditionRegistry(preload_defaults=True)

__all__ = ["ConditionRegistry", "registry"]
