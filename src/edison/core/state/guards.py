from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional


class GuardRegistry:
    """Registry of guard functions keyed by name."""

    def __init__(self, *, preload_defaults: bool = False) -> None:
        self._guards: Dict[str, Callable[[Mapping[str, Any]], bool]] = {}
        if preload_defaults:
            self.register_defaults()

    def register(self, name: str, guard_fn: Callable[[Mapping[str, Any]], bool]) -> None:
        if not callable(guard_fn):
            raise TypeError("guard_fn must be callable")
        self._guards[name] = guard_fn

    def register_defaults(self) -> None:
        for name, fn in _DEFAULT_GUARDS.items():
            self._guards.setdefault(name, fn)

    def reset(self) -> None:
        self._guards.clear()
        self.register_defaults()

    def check(self, name: str, context: Optional[Mapping[str, Any]] = None) -> bool:
        if name not in self._guards:
            raise ValueError(f"Unknown guard: {name}")
        ctx = context or {}
        return bool(self._guards[name](ctx))


# Built-in guards used by default configuration. They are intentionally light-
# weight to keep behavior deterministic in tests while still exercising the
# declarative pipeline.

def _guard_always_allow(context: Mapping[str, Any]) -> bool:
    return True


def _guard_can_activate_session(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    if not isinstance(session, Mapping):
        return True
    # Require at least one linked task when available; otherwise allow.
    task_count = session.get("task_count") or len(session.get("tasks", []) or [])
    claimed = session.get("claimed", True)
    if task_count == 0:
        return True
    return bool(claimed)


def _guard_can_complete_session(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    return bool(session.get("ready_to_complete", True))


def _guard_has_blockers(context: Mapping[str, Any]) -> bool:
    session = context.get("session", {}) if isinstance(context, Mapping) else {}
    if not session:
        # In lightweight CLI flows we often lack rich context; allow the
        # transition rather than blocking on missing metadata.
        return True
    return bool(session.get("blocked") or session.get("blockers"))


def _guard_task_can_start(context: Mapping[str, Any]) -> bool:
    task = context.get("task", {}) if isinstance(context, Mapping) else {}
    return bool(task.get("allowed", True))


def _guard_task_can_finish(context: Mapping[str, Any]) -> bool:
    task = context.get("task", {}) if isinstance(context, Mapping) else {}
    return bool(task.get("ready_for_validation", True))


_DEFAULT_GUARDS: Dict[str, Callable[[Mapping[str, Any]], bool]] = {
    "always_allow": _guard_always_allow,
    "can_activate_session": _guard_can_activate_session,
    "can_complete_session": _guard_can_complete_session,
    "has_blockers": _guard_has_blockers,
    "can_start_task": _guard_task_can_start,
    "can_finish_task": _guard_task_can_finish,
}


registry = GuardRegistry(preload_defaults=True)

__all__ = ["GuardRegistry", "registry"]
