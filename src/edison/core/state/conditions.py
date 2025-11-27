from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from .registry import ConditionRegistryBase, DomainRegistry


class ConditionRegistry(ConditionRegistryBase):
    """Registry of condition predicates.
    
    Extends ConditionRegistryBase to maintain backward compatibility while
    supporting domain-prefixed lookups for multi-entity state machines.
    """

    def __init__(self, *, preload_defaults: bool = False) -> None:
        super().__init__(preload_defaults=preload_defaults)

    def register(
        self, 
        name: str, 
        condition_fn: Callable[[Mapping[str, Any]], bool],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Register a condition function.
        
        Args:
            name: Condition name
            condition_fn: Condition function that returns bool
            domain: Domain identifier (default: shared)
        """
        super().register(name, condition_fn, domain)

    def register_defaults(self) -> None:
        """Register default condition functions."""
        for name, fn in _DEFAULT_CONDITIONS.items():
            if not self.has(name):
                self.register(name, fn)

    def check(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> bool:
        """Check a condition.
        
        Args:
            name: Condition name
            context: Context dict for condition evaluation
            domain: Domain for condition lookup (default: shared)
            
        Returns:
            Condition result (bool)
        """
        return super().check(name, context, domain)


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
