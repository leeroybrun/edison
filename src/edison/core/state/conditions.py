"""Condition registry for state machine transitions.

Conditions are boolean predicates that check prerequisites for transitions.
Conditions are loaded dynamically from data/conditions/ via the handler loader.

Conditions support OR logic for alternative conditions in workflow.yaml:
```yaml
conditions:
  - name: validation_failed
    or:
      - name: dependencies_missing
```
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from .handlers import ConditionRegistryBase, DomainRegistry


class ConditionRegistry(ConditionRegistryBase):
    """Registry of condition predicates.
    
    Conditions are loaded from data/conditions/ with layered composition:
    - Core: data/conditions/
    - Bundled packs: data/packs/<pack>/conditions/
    - Project packs: .edison/packs/<pack>/conditions/
    - Project: .edison/conditions/
    
    Later layers override earlier ones.
    """

    def __init__(self, *, preload_defaults: bool = False) -> None:
        """Initialize registry.
        
        Args:
            preload_defaults: Ignored (conditions are loaded via handler loader)
        """
        super().__init__(preload_defaults=False)

    def register(
        self, 
        name: str, 
        condition_fn: Callable[[Mapping[str, Any]], bool],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Register a condition function.
        
        Args:
            name: Condition name
            condition_fn: Condition function that returns bool
            domain: Domain identifier (default: shared)
        """
        super().register(name, condition_fn, domain)

    def add(
        self, 
        name: str, 
        condition_fn: Callable[[Mapping[str, Any]], bool],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> None:
        """Add a condition function (alias for register).
        
        Args:
            name: Condition name
            condition_fn: Condition function that returns bool
            domain: Domain identifier (default: shared)
        """
        self.register(name, condition_fn, domain)

    def register_defaults(self) -> None:
        """No-op: conditions are loaded dynamically via handler loader."""
        pass

    def check(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> bool:
        """Check a condition.
        
        Args:
            name: Condition name
            context: Context dict for condition evaluation
            domain: Domain for condition lookup (default: shared)
            
        Returns:
            Condition result (bool)
        """
        return super().check(name, context, domain)


# Global registry instance
registry = ConditionRegistry()

__all__ = ["ConditionRegistry", "registry"]
