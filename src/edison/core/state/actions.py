from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional


class ActionRegistry:
    """Registry of post-transition actions."""

    def __init__(self, *, preload_defaults: bool = False) -> None:
        self._actions: Dict[str, Callable[[MutableMapping[str, Any]], Any]] = {}
        if preload_defaults:
            self.register_defaults()

    def register(self, name: str, action_fn: Callable[[MutableMapping[str, Any]], Any]) -> None:
        if not callable(action_fn):
            raise TypeError("action_fn must be callable")
        self._actions[name] = action_fn

    def register_defaults(self) -> None:
        for name, fn in _DEFAULT_ACTIONS.items():
            self._actions.setdefault(name, fn)

    def reset(self) -> None:
        self._actions.clear()
        self.register_defaults()

    def execute(self, name: str, context: Optional[MutableMapping[str, Any]] = None) -> Any:
        if name not in self._actions:
            raise ValueError(f"Unknown action: {name}")
        ctx = context or {}
        return self._actions[name](ctx)


def _record_action(context: MutableMapping[str, Any], label: str) -> None:
    try:
        context.setdefault("_actions", []).append(label)
    except Exception:
        pass


def _action_create_worktree(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "create_worktree")


def _action_record_activation_time(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "record_activation_time")


def _action_notify_session_start(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "notify_session_start")


def _action_finalize_session(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "finalize_session")


def _action_record_completion_time(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "record_completion_time")


def _action_record_blocker_reason(context: MutableMapping[str, Any]) -> None:
    reason = None
    if isinstance(context, Mapping):
        session = context.get("session", {}) if isinstance(context.get("session", {}), Mapping) else {}
        reason = session.get("reason")
    _record_action(context, f"record_blocker_reason:{reason or ''}")


def _action_record_closed(context: MutableMapping[str, Any]) -> None:
    _record_action(context, "record_closed")


_DEFAULT_ACTIONS: Dict[str, Callable[[MutableMapping[str, Any]], Any]] = {
    "create_worktree": _action_create_worktree,
    "record_activation_time": _action_record_activation_time,
    "notify_session_start": _action_notify_session_start,
    "finalize_session": _action_finalize_session,
    "record_completion_time": _action_record_completion_time,
    "record_blocker_reason": _action_record_blocker_reason,
    "record_closed": _action_record_closed,
}


registry = ActionRegistry(preload_defaults=True)

__all__ = ["ActionRegistry", "registry"]
