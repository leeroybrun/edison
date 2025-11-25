"""State-machine helpers for tasks and QA records."""
from __future__ import annotations

from typing import Any, Dict, Tuple

from ..exceptions import TaskStateError
from ..rules import RulesEngine
from .io import qa_progress, ready_task, _now_iso, load_task_record, update_task_record
from .metadata import validate_state_transition


def transition_task(task_id: str, to_state: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Transition task to new state with rules enforcement."""
    if config is None:
        from ..config import ConfigManager  # type: ignore

        config = ConfigManager().load_config(validate=False)

    task = load_task_record(task_id)
    from_state = str(task.get("state") or task.get("status") or "todo")

    ok, msg = validate_state_transition("task", from_state, to_state)
    if not ok:
        raise TaskStateError(msg, context={"taskId": task_id, "from": from_state, "to": to_state})

    engine = RulesEngine(config)
    violations = engine.check_state_transition(task, from_state, to_state)

    if violations:
        non_blocking = [v for v in violations if v.severity == "warning"]
        if non_blocking:
            print(f"⚠️  Task {task_id}: {len(non_blocking)} rule warnings")
            for v in non_blocking:
                print(f"  - {v.rule.description}")
                if v.rule.reference:
                    print(f"    See: {v.rule.reference}")

    task["state"] = to_state
    history = list(task.get("stateHistory") or [])
    history.append(
        {
            "from": from_state,
            "to": to_state,
            "timestamp": _now_iso(),
            "ruleViolations": [v.rule.id for v in violations if v.severity == "warning"],
        }
    )
    task["stateHistory"] = history

    update_task_record(task_id, task, operation="transition")
    return task


__all__ = [
    "validate_state_transition",
    "ready_task",
    "qa_progress",
    "transition_task",
]
