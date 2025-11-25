from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ..exceptions import EdisonError
from .guards import GuardRegistry
from .conditions import ConditionRegistry
from .actions import ActionRegistry


class StateTransitionError(EdisonError, ValueError):
    """Raised when a declarative state transition fails."""

    def __init__(self, message: str = "", *, context: Optional[Mapping[str, Any]] = None) -> None:
        EdisonError.__init__(self, message, context=context)
        ValueError.__init__(self, message)


def _flatten_transitions(states: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Return a simple from->to adjacency map from rich state definitions."""
    trans: Dict[str, List[str]] = {}
    for state_name, info in (states or {}).items():
        allowed = []
        for t in (info or {}).get("allowed_transitions", []) or []:
            to_state = t.get("to")
            if to_state:
                allowed.append(str(to_state))
        trans[str(state_name)] = allowed
    return trans


def _resolve_path(context: Mapping[str, Any], dotted: str) -> Any:
    current: Any = context
    for part in dotted.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current.get(part)
        else:
            return None
    return current


class RichStateMachine:
    """Declarative state machine with guard/condition/action support."""

    def __init__(
        self,
        name: str,
        spec: Mapping[str, Any],
        guards: GuardRegistry,
        conditions: ConditionRegistry,
        actions: ActionRegistry,
    ):
        self.name = name
        self.spec = spec or {}
        states = self.spec.get("states") or {}
        if not isinstance(states, Mapping):
            raise ValueError(f"State machine '{name}' requires a mapping of states")
        self.states: Mapping[str, Any] = states
        self.guards = guards
        self.conditions = conditions
        self.actions = actions

    def allowed_targets(self, current: str) -> List[str]:
        if current is None:
            return []
        info = self.states.get(str(current)) or {}
        transitions = info.get("allowed_transitions") or []
        return [t.get("to") for t in transitions if t.get("to")]

    def _find_transition(self, current: str, target: str) -> Optional[Mapping[str, Any]]:
        info = self.states.get(str(current)) or {}
        for t in info.get("allowed_transitions", []) or []:
            if t.get("to") == target:
                return t
        return None

    def _check_guard(self, transition: Mapping[str, Any], ctx: Mapping[str, Any]) -> None:
        guard_name = transition.get("guard")
        if not guard_name:
            return
        result = self.guards.check(str(guard_name), ctx)
        if not result:
            raise StateTransitionError(
                f"Guard '{guard_name}' blocked transition",
                context={"domain": self.name, "guard": guard_name},
            )

    def _check_condition(self, cond: Mapping[str, Any], ctx: Mapping[str, Any]) -> None:
        name = cond.get("name")
        if not name:
            return
        passed = bool(self.conditions.check(str(name), ctx))
        if not passed:
            for alt in cond.get("or", []) or []:
                alt_name = alt.get("name")
                if alt_name and self.conditions.check(str(alt_name), ctx):
                    passed = True
                    break
        if not passed:
            message = cond.get("error") or f"Condition '{name}' failed"
            raise StateTransitionError(
                message,
                context={"domain": self.name, "condition": name},
            )

    def _run_conditions(self, transition: Mapping[str, Any], ctx: Mapping[str, Any]) -> None:
        for cond in transition.get("conditions", []) or []:
            self._check_condition(cond or {}, ctx)

    def _should_execute(self, action_spec: Mapping[str, Any], ctx: Mapping[str, Any]) -> bool:
        flag = action_spec.get("when")
        if flag is None:
            return True
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            val = _resolve_path(ctx, flag)
            return bool(val)
        return bool(flag)

    def _run_actions(self, transition: Mapping[str, Any], ctx: Mapping[str, Any]) -> None:
        for action in transition.get("actions", []) or []:
            if not isinstance(action, Mapping):
                continue
            if not self._should_execute(action, ctx):
                continue
            name = action.get("name")
            if not name:
                continue
            self.actions.execute(str(name), ctx)

    def validate(self, current: str, target: str, *, context: Optional[Mapping[str, Any]] = None, execute_actions: bool = True) -> bool:
        ctx = context or {}
        if current == target:
            return True
        transition = self._find_transition(str(current), str(target))
        if transition is None:
            raise StateTransitionError(
                f"Invalid transition {current!r} -> {target!r}",
                context={"domain": self.name, "from": current, "to": target},
            )
        self._check_guard(transition, ctx)
        self._run_conditions(transition, ctx)
        if execute_actions:
            self._run_actions(transition, ctx)
        return True

    def transitions_map(self) -> Dict[str, List[str]]:
        return _flatten_transitions(self.states)


__all__ = [
    "RichStateMachine",
    "StateTransitionError",
    "_flatten_transitions",
]
