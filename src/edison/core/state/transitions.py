"""Unified state transition logic for all entity types.

This module provides a generic transition function that works with any
stateful entity through the repository pattern. It handles:

- State validation using RichStateMachine
- Guard checking via DomainRegistry
- Condition evaluation via DomainRegistry  
- Action execution via DomainRegistry
- State history tracking

Usage:
    from edison.core.state.transitions import transition_entity
    
    # Transition a task
    task = transition_entity(
        entity_type="task",
        entity_id="task-123",
        to_state="done",
        repository=task_repository,
    )
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Protocol, TYPE_CHECKING

from .engine import StateTransitionError

if TYPE_CHECKING:
    from edison.core.entity.protocols import StatefulEntity
    from edison.core.entity.repository import BaseRepository


class StateMachineProvider(Protocol):
    """Protocol for objects that provide state machine configuration."""
    
    def get_state_machine(self, entity_type: str) -> RichStateMachine:
        """Get the state machine for an entity type."""
        ...


class EntityTransitionError(StateTransitionError):
    """Error during entity state transition."""
    
    def __init__(
        self,
        message: str,
        *,
        entity_type: str,
        entity_id: str,
        from_state: str,
        to_state: str,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason




def validate_transition(
    entity_type: str,
    from_state: str,
    to_state: str,
    *,
    context: Optional[Mapping[str, Any]] = None,
) -> tuple[bool, str]:
    """Validate a state transition without executing it.

    This function delegates to StateValidator for canonical validation logic.

    Args:
        entity_type: Entity type ("task", "session", "qa")
        from_state: Current state
        to_state: Target state
        context: Optional context for guard/condition evaluation

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for missing current state
    if not from_state or from_state.strip() == "":
        return False, "Missing current status"

    if from_state == to_state:
        return True, ""

    # Delegate to StateValidator as the canonical validation entry point
    from edison.core.state.validator import StateValidator, MissingStateMachine

    try:
        validator = StateValidator()
        validator.ensure_transition(
            entity=entity_type,
            current=from_state,
            target=to_state,
            context=context,
        )
        return True, ""
    except MissingStateMachine:
        # No state machine configured - allow all transitions
        return True, ""
    except StateTransitionError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def transition_entity(
    entity_type: str,
    entity_id: str,
    to_state: str,
    *,
    current_state: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    record_history: bool = True,
) -> Dict[str, Any]:
    """Execute a state transition for any entity type.
    
    This is a generic transition function that:
    1. Validates the transition is allowed
    2. Checks guards and conditions
    3. Executes post-transition actions
    4. Returns the updated entity state
    
    Args:
        entity_type: Entity type ("task", "session", "qa")
        entity_id: Entity identifier
        to_state: Target state
        current_state: Current state (if not provided, defaults to "todo")
        context: Context dict for guards/conditions/actions
        record_history: Whether to record state history
        
    Returns:
        Dict with updated state and optional history
        
    Raises:
        EntityTransitionError: If transition is not allowed
    """
    from_state = current_state or "todo"
    ctx = dict(context or {})
    ctx["entity_type"] = entity_type
    ctx["entity_id"] = entity_id
    
    # Validate transition
    valid, error = validate_transition(entity_type, from_state, to_state, context=ctx)
    if not valid:
        raise EntityTransitionError(
            error,
            entity_type=entity_type,
            entity_id=entity_id,
            from_state=from_state,
            to_state=to_state,
            reason=error,
        )
    
    # Build result
    result: Dict[str, Any] = {
        "state": to_state,
        "previous_state": from_state,
    }
    
    # Record history if requested
    if record_history:
        from edison.core.utils.time import utc_timestamp
        history_entry = {
            "from": from_state,
            "to": to_state,
            "timestamp": utc_timestamp(),
        }
        result["history_entry"] = history_entry
    
    # Execute actions for the target state (if machine exists)
    # Use StateValidator's machine for action execution
    from edison.core.state.validator import StateValidator, MissingStateMachine

    try:
        validator = StateValidator()
        machine = validator._machine(entity_type)
        # Validate and execute actions
        machine.validate(from_state, to_state, context=ctx, execute_actions=True)
    except MissingStateMachine:
        # No state machine configured - skip action execution
        pass
    except StateTransitionError:
        # Already validated, so this shouldn't happen
        pass
    
    # Record any executed actions in result
    if "_actions" in ctx:
        result["actions_executed"] = ctx["_actions"]
    
    return result


__all__ = [
    "EntityTransitionError",
    "validate_transition",
    "transition_entity",
]


