"""State machine helpers for legacy ``lib.tasks`` import path."""
from __future__ import annotations

from edison.core.task.config import TaskConfig
from edison.core.state import RichStateMachine, guard_registry, condition_registry, action_registry


def build_default_state_machine() -> RichStateMachine:
    """Return a RichStateMachine seeded from config for task domain."""
    cfg = TaskConfig()
    spec = (cfg._state_machine() if hasattr(cfg, "_state_machine") else {})  # type: ignore[attr-defined]
    task_spec = (spec.get("task") if isinstance(spec, dict) else {}) or {}
    return RichStateMachine("task", task_spec, guard_registry, condition_registry, action_registry)


__all__ = ["build_default_state_machine"]

