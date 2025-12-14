"""Guard registry for state machine transitions.

Guards are boolean functions that determine if a transition is allowed.
Guards are loaded dynamically via the handler loader (builtin + pack + project layers).

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed  
- Only return True when all conditions are explicitly met
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from .handlers.registries import GuardRegistryBase, DomainRegistry


class GuardRegistry(GuardRegistryBase):
    """Registry of guard functions keyed by name.
    
    Guards are loaded with layered composition:
    - Core (builtin): core/state/builtin/guards/
    - Bundled packs: data/packs/<pack>/guards/
    - Project packs: .edison/packs/<pack>/guards/
    - Project: .edison/guards/
    
    Later layers override earlier ones.
    """

    def __init__(self, *, preload_defaults: bool = False) -> None:
        """Initialize registry.
        
        Args:
            preload_defaults: Ignored (guards are loaded via handler loader)
        """
        super().__init__(preload_defaults=False)

    def register(
        self, 
        name: str, 
        guard_fn: Callable[[Mapping[str, Any]], bool],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Register a guard function.
        
        Args:
            name: Guard name
            guard_fn: Guard function that returns bool
            domain: Domain identifier (default: shared)
        """
        super().register(name, guard_fn, domain)

    def add(
        self, 
        name: str, 
        guard_fn: Callable[[Mapping[str, Any]], bool],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Add a guard function (alias for register).
        
        Args:
            name: Guard name
            guard_fn: Guard function that returns bool
            domain: Domain identifier (default: shared)
        """
        self.register(name, guard_fn, domain)

    def register_defaults(self) -> None:
        """Register builtin guards.

        IMPORTANT: Tests (and some tooling) call `registry.reset()` to ensure a clean
        slate. `reset()` is defined on the shared DomainRegistry base and calls
        `register_defaults()` afterwards. If this is a no-op, a single test that
        resets the registry will permanently remove builtin guards for the rest of
        the process, causing cross-test flakiness (e.g. `can_complete_session`).
        """
        try:
            from edison.core.state.loader import load_guards

            # Load only builtin/core handlers by default. Project/pack layers are
            # loaded by `edison.core.state.load_handlers(...)` when needed.
            load_guards(project_root=None, active_packs=[])
        except Exception:
            # Fail-closed for callers that rely on explicit registrations.
            pass

    def check(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> bool:
        """Check a guard condition.
        
        Args:
            name: Guard name
            context: Context dict for guard evaluation
            domain: Domain for guard lookup (default: shared)
            
        Returns:
            Guard result (bool)
        """
        return super().check(name, context, domain)


# Global registry instance
registry = GuardRegistry()

__all__ = ["GuardRegistry", "registry"]
