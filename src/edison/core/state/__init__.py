from .engine import RichStateMachine, StateTransitionError, _flatten_transitions
from .registry import (
    DomainRegistry,
    GuardRegistryBase,
    ConditionRegistryBase,
    ActionRegistryBase,
)
from .guards import GuardRegistry, registry as guard_registry
from .conditions import ConditionRegistry, registry as condition_registry
from .actions import ActionRegistry, registry as action_registry
from .transitions import (
    EntityTransitionError,
    validate_transition,
    transition_entity,
)

__all__ = [
    # Core state machine
    "RichStateMachine",
    "StateTransitionError",
    "_flatten_transitions",
    # Registry base classes
    "DomainRegistry",
    "GuardRegistryBase",
    "ConditionRegistryBase",
    "ActionRegistryBase",
    # Concrete registries
    "GuardRegistry",
    "ConditionRegistry",
    "ActionRegistry",
    # Global registry instances
    "guard_registry",
    "condition_registry",
    "action_registry",
    # Unified transitions
    "EntityTransitionError",
    "validate_transition",
    "transition_entity",
]
