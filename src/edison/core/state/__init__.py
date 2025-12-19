from .engine import RichStateMachine, StateTransitionError, _flatten_transitions
from .handlers.registries import (
    DomainRegistry,
    GuardRegistryBase,
    ConditionRegistryBase,
    ActionRegistryBase,
    # Registration decorators
    register_guard,
    register_action,
    register_condition,
)
from .guards import GuardRegistry, registry as guard_registry
from .conditions import ConditionRegistry, registry as condition_registry
from .actions import ActionRegistry, registry as action_registry
from .transitions import (
    EntityTransitionError,
    validate_transition,
    transition_entity,
)
from .loader import load_handlers, load_guards, load_actions, load_conditions


def _init_handlers() -> None:
    """Initialize handlers from layered data folders.
    
    Called automatically on module import to load handlers from:
    1. Core: data/guards/, data/actions/, data/conditions/
    2. Bundled packs: data/packs/<pack>/...
    3. Project packs: <project-config-dir>/packs/<pack>/...
    4. Project: <project-config-dir>/guards|actions|conditions/
    """
    try:
        load_handlers()
    except Exception:
        # Handler loading should not break module import
        pass


# Auto-load handlers on module import
_init_handlers()


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
    # Registration decorators
    "register_guard",
    "register_action",
    "register_condition",
    # Loader functions
    "load_handlers",
    "load_guards",
    "load_actions",
    "load_conditions",
]
