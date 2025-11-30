import pytest
import yaml

from edison.core.state import RichStateMachine, StateTransitionError
from edison.core.state.guards import GuardRegistry
from edison.core.state.conditions import ConditionRegistry
from edison.core.state.actions import ActionRegistry


def _session_spec(tmp_path):
    spec = {
        "statemachine": {
            "session": {
                "states": {
                    "draft": {
                        "description": "Session in draft state, not yet active",
                        "allowed_transitions": [
                            {
                                "to": "active",
                                "guard": "can_activate_session",
                                "conditions": [
                                    {"name": "has_task", "error": "Session must have a linked task"},
                                    {"name": "task_claimed", "error": "Task must be claimed before activating session"},
                                ],
                                "actions": [
                                    {"name": "record_activation_time"},
                                    {"name": "notify_session_start", "when": "config.notify"},
                                ],
                            }
                        ],
                    },
                    "active": {
                        "allowed_transitions": [
                            {
                                "to": "blocked",
                                "guard": "has_blockers",
                                "conditions": [
                                    {"name": "validation_failed", "or": [{"name": "dependencies_missing"}]},
                                ],
                                "actions": [
                                    {"name": "record_blocker_reason"}
                                ],
                            },
                            {"to": "done", "actions": [{"name": "record_completion_time"}]},
                        ]
                    },
                    "blocked": {"allowed_transitions": []},
                    "done": {"allowed_transitions": []},
                }
            }
        }
    }
    p = tmp_path / "state-machine.yaml"
    p.write_text(yaml.dump(spec), encoding="utf-8")
    return spec["statemachine"]["session"]


def test_guard_condition_action_flow(tmp_path):
    session_spec = _session_spec(tmp_path)

    guards = GuardRegistry()
    conditions = ConditionRegistry()
    actions = ActionRegistry()

    calls = {"guards": [], "conditions": [], "actions": []}

    guards.register("can_activate_session", lambda ctx: calls["guards"].append("activate") or ctx["session"].get("ready", False))
    guards.register("has_blockers", lambda ctx: calls["guards"].append("blockers") or bool(ctx["session"].get("blocked")))

    conditions.register("has_task", lambda ctx: calls["conditions"].append("has_task") or ctx["session"].get("task_count", 0) > 0)
    conditions.register("task_claimed", lambda ctx: calls["conditions"].append("task_claimed") or ctx["session"].get("claimed", False))
    conditions.register("validation_failed", lambda ctx: calls["conditions"].append("validation_failed") or ctx["session"].get("validation_failed", False))
    conditions.register("dependencies_missing", lambda ctx: calls["conditions"].append("dependencies_missing") or ctx["session"].get("deps_missing", False))

    actions.register("record_activation_time", lambda ctx: (calls["actions"].append("record_activation_time")))
    actions.register("notify_session_start", lambda ctx: (calls["actions"].append("notify_session_start")))
    actions.register("record_blocker_reason", lambda ctx: (calls["actions"].append(f"blocker:{ctx['session'].get('reason', '')}")))
    actions.register("record_completion_time", lambda ctx: (calls["actions"].append("record_completion_time")))

    sm = RichStateMachine("session", session_spec, guards, conditions, actions)

    ctx = {"session": {"ready": True, "task_count": 1, "claimed": True}, "config": {"notify": True}}
    assert sm.validate("draft", "active", context=ctx) is True
    assert "activate" in calls["guards"]
    assert set(calls["conditions"]) >= {"has_task", "task_claimed"}
    assert "record_activation_time" in calls["actions"]
    assert "notify_session_start" in calls["actions"]

    # OR condition branch: validation_failed False but deps_missing True should pass
    ctx_blocked = {"session": {"blocked": True, "validation_failed": False, "deps_missing": True, "reason": "deps"}}
    assert sm.validate("active", "blocked", context=ctx_blocked) is True
    assert "blocker:deps" in calls["actions"]

    # Guard failure stops transition
    ctx_denied = {"session": {"ready": False, "task_count": 1, "claimed": True}, "config": {"notify": False}}
    with pytest.raises(StateTransitionError):
        sm.validate("draft", "active", context=ctx_denied)

    # Condition failure stops transition
    ctx_missing = {"session": {"ready": True, "task_count": 0, "claimed": False}}
    with pytest.raises(StateTransitionError):
        sm.validate("draft", "active", context=ctx_missing)


def test_allowed_targets_exposed(tmp_path):
    session_spec = _session_spec(tmp_path)
    sm = RichStateMachine("session", session_spec, GuardRegistry(), ConditionRegistry(), ActionRegistry())
    assert sm.allowed_targets("draft") == ["active"]
    assert sm.allowed_targets("done") == []
