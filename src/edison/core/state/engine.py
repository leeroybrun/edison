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
        try:
            result = self.guards.check(str(guard_name), ctx)
            try:
                from edison.core.audit.logger import audit_event

                audit_event(
                    "guard.check",
                    domain=self.name,
                    guard=str(guard_name),
                    to=transition.get("to"),
                    result=bool(result),
                )
            except Exception:
                pass
        except Exception as exc:
            try:
                from edison.core.audit.logger import audit_event

                audit_event(
                    "guard.error",
                    domain=self.name,
                    guard=str(guard_name),
                    to=transition.get("to"),
                    error=str(exc),
                )
            except Exception:
                pass
            raise StateTransitionError(
                str(exc),
                context={"domain": self.name, "guard": guard_name},
            ) from exc
        if not result:
            try:
                from edison.core.audit.logger import audit_event

                audit_event(
                    "guard.blocked",
                    domain=self.name,
                    guard=str(guard_name),
                    to=transition.get("to"),
                )
            except Exception:
                pass
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

    def _get_action_timing(self, action_spec: Mapping[str, Any]) -> str:
        """Get the timing for an action (before or after transition).
        
        Returns:
            'before' - Execute before guards/conditions
            'after' - Execute after successful transition (default)
        """
        when = action_spec.get("when")
        if when in ("before", "after"):
            return when
        # Default to 'after' for all other cases (including conditional when)
        return "after"

    def _should_execute_conditional(self, action_spec: Mapping[str, Any], ctx: Mapping[str, Any]) -> bool:
        """Check if a conditional action should execute.
        
        Handles:
        - Boolean `when:` values
        - Config path resolution like `when: config.worktrees_enabled`
        - No `when:` specified (always execute)
        
        Note: 'before'/'after' timing is handled by _get_action_timing,
        so those values skip conditional checks.
        """
        flag = action_spec.get("when")
        if flag is None:
            return True
        # Timing values - always execute (timing handled separately)
        if flag in ("before", "after"):
            return True
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            val = _resolve_path(ctx, flag)
            return bool(val)
        return bool(flag)

    def _run_actions(
        self, 
        transition: Mapping[str, Any], 
        ctx: Mapping[str, Any],
        timing: str = "after"
    ) -> None:
        """Run actions for a transition filtered by timing.
        
        Args:
            transition: Transition spec from state machine config
            ctx: Context dict for action execution
            timing: 'before' or 'after' - only actions with matching timing are executed
        """
        for action in transition.get("actions", []) or []:
            if not isinstance(action, Mapping):
                continue
            
            # Check timing first
            action_timing = self._get_action_timing(action)
            if action_timing != timing:
                continue
            
            # Check conditional execution
            if not self._should_execute_conditional(action, ctx):
                continue
            
            name = action.get("name")
            if not name:
                continue
            
            self.actions.execute(str(name), ctx)

    def validate(
        self, 
        current: str, 
        target: str, 
        *, 
        context: Optional[Mapping[str, Any]] = None, 
        execute_actions: bool = True
    ) -> bool:
        """Validate and optionally execute a state transition.
        
        Execution order:
        1. Pre-transition actions (when: before)
        2. Guard check
        3. Condition checks
        4. Post-transition actions (when: after, default)
        
        Args:
            current: Current state
            target: Target state
            context: Context dict for guards/conditions/actions
            execute_actions: Whether to execute actions (default: True)
            
        Returns:
            True if transition is valid
            
        Raises:
            StateTransitionError: If transition is not allowed or guards/conditions fail
        """
        ctx = context or {}
        if current == target:
            return True
        
        transition = self._find_transition(str(current), str(target))
        if transition is None:
            raise StateTransitionError(
                f"Invalid transition {current!r} -> {target!r}: not allowed",
                context={"domain": self.name, "from": current, "to": target},
            )
        
        # 1. Pre-transition actions (when: before)
        if execute_actions:
            self._run_actions(transition, ctx, timing="before")
        
        # 2. Guard check
        self._check_guard(transition, ctx)
        
        # 3. Condition checks
        self._run_conditions(transition, ctx)
        
        # 4. Post-transition actions (when: after, default)
        if execute_actions:
            self._run_actions(transition, ctx, timing="after")
        
        return True

    def transitions_map(self) -> Dict[str, List[str]]:
        return _flatten_transitions(self.states)


__all__ = [
    "RichStateMachine",
    "StateTransitionError",
    "_flatten_transitions",
]
