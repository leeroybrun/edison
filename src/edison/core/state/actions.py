"""Action registry for state machine transitions.

Actions are side-effect functions executed during state transitions.
Actions are loaded dynamically from data/actions/ via the handler loader.

Actions can be configured to run:
- `when: before` - Before guard/condition checks
- `when: after` - After successful transition (default)
- `when: config.path` - Conditionally based on config value
"""
from __future__ import annotations

from typing import Any, Callable, MutableMapping, Optional

from .handlers.registries import ActionRegistryBase, DomainRegistry


class ActionRegistry(ActionRegistryBase):
    """Registry of transition actions.
    
    Actions are loaded from data/actions/ with layered composition:
    - Core: data/actions/
    - Bundled packs: data/packs/<pack>/actions/
    - Project packs: .edison/packs/<pack>/actions/
    - Project: .edison/actions/
    
    Later layers override earlier ones.
    """

    def __init__(self, *, preload_defaults: bool = False) -> None:
        """Initialize registry.
        
        Args:
            preload_defaults: Ignored (actions are loaded via handler loader)
        """
        super().__init__(preload_defaults=False)

    def register(
        self, 
        name: str, 
        action_fn: Callable[[MutableMapping[str, Any]], Any],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Register an action function.
        
        Args:
            name: Action name
            action_fn: Action function
            domain: Domain identifier (default: shared)
        """
        super().register(name, action_fn, domain)

    def add(
        self, 
        name: str, 
        action_fn: Callable[[MutableMapping[str, Any]], Any],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Add an action function (alias for register).
        
        Args:
            name: Action name
            action_fn: Action function
            domain: Domain identifier (default: shared)
        """
        self.register(name, action_fn, domain)

    def register_defaults(self) -> None:
        """No-op: actions are loaded dynamically via handler loader."""
        pass

    def execute(
        self, 
        name: str, 
        context: Optional[MutableMapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> Any:
        """Execute an action.
        
        Args:
            name: Action name
            context: Context dict for action execution
            domain: Domain for action lookup (default: shared)
            
        Returns:
            Action result
        """
        return super().execute(name, context, domain)


# Global registry instance
registry = ActionRegistry()

__all__ = ["ActionRegistry", "registry"]
