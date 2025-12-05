"""Generic domain-aware registry for state machine handlers.

This module provides a base registry class that supports domain-prefixed
lookups, allowing the same handler names to be registered with different
implementations per domain (task, session, qa, etc.).

Example usage:
    registry.register("can_transition", handler_fn, domain="task")
    registry.register("can_transition", other_handler_fn, domain="session")
    
    # Lookup with domain-specific handler
    registry.get("can_transition", domain="task")  # Returns handler_fn
    registry.get("can_transition", domain="session")  # Returns other_handler_fn
    
    # Fallback to shared handler if domain-specific not found
    registry.register("always_allow", shared_fn)  # No domain = shared
    registry.get("always_allow", domain="task")  # Falls back to shared
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, Mapping, Optional, TypeVar

# Type variable for handler functions
T = TypeVar("T", bound=Callable[..., Any])


class DomainRegistry(Generic[T], ABC):
    """Generic registry with domain-aware handler lookups.
    
    Handlers can be registered with an optional domain prefix. When looking up
    a handler, the registry first tries the domain-specific key, then falls
    back to the shared (non-prefixed) handler if not found.
    
    Attributes:
        SHARED_DOMAIN: Constant for handlers that apply to all domains
    """
    
    SHARED_DOMAIN = "shared"
    
    def __init__(self, *, preload_defaults: bool = False) -> None:
        """Initialize registry.
        
        Args:
            preload_defaults: If True, register default handlers on init
        """
        self._handlers: Dict[str, T] = {}
        if preload_defaults:
            self.register_defaults()
    
    def _make_key(self, name: str, domain: str = SHARED_DOMAIN) -> str:
        """Create registry key from name and domain.
        
        Args:
            name: Handler name
            domain: Domain identifier (default: shared)
            
        Returns:
            Registry key with optional domain prefix
        """
        if domain == self.SHARED_DOMAIN:
            return name
        return f"{domain}:{name}"
    
    def register(self, name: str, handler: T, domain: str = SHARED_DOMAIN) -> None:
        """Register a handler function.
        
        Args:
            name: Handler name (unique within domain)
            handler: Callable handler function
            domain: Domain identifier (default: shared)
            
        Raises:
            TypeError: If handler is not callable
        """
        if not callable(handler):
            raise TypeError("handler must be callable")
        key = self._make_key(name, domain)
        self._handlers[key] = handler
    
    def add(self, name: str, handler: T, domain: str = SHARED_DOMAIN) -> None:
        """Add a handler function (alias for register).
        
        Args:
            name: Handler name (unique within domain)
            handler: Callable handler function
            domain: Domain identifier (default: shared)
        """
        self.register(name, handler, domain)
    
    def get(self, name: str, domain: str = SHARED_DOMAIN) -> Optional[T]:
        """Get a handler by name, with domain fallback.
        
        Lookup priority:
        1. Domain-specific: "{domain}:{name}"
        2. Shared: "{name}"
        
        Args:
            name: Handler name
            domain: Domain to look up (default: shared)
            
        Returns:
            Handler function or None if not found
        """
        # Try domain-specific first
        if domain != self.SHARED_DOMAIN:
            key = self._make_key(name, domain)
            if key in self._handlers:
                return self._handlers[key]
        
        # Fall back to shared
        if name in self._handlers:
            return self._handlers[name]
        
        return None
    
    def has(self, name: str, domain: str = SHARED_DOMAIN) -> bool:
        """Check if a handler exists.
        
        Args:
            name: Handler name
            domain: Domain to check (default: shared)
            
        Returns:
            True if handler exists for domain or shared
        """
        return self.get(name, domain) is not None
    
    def list_handlers(self, domain: Optional[str] = None) -> Dict[str, T]:
        """List all handlers, optionally filtered by domain.
        
        Args:
            domain: If provided, only return handlers for this domain
                    (including shared handlers accessible to this domain)
                    
        Returns:
            Dict of handler names to handlers
        """
        if domain is None:
            return dict(self._handlers)
        
        result: Dict[str, T] = {}
        prefix = f"{domain}:"
        
        for key, handler in self._handlers.items():
            if key.startswith(prefix):
                # Domain-specific handler
                name = key[len(prefix):]
                result[name] = handler
            elif ":" not in key:
                # Shared handler (no prefix)
                if key not in result:  # Don't override domain-specific
                    result[key] = handler
        
        return result
    
    def reset(self) -> None:
        """Clear all handlers and reload defaults."""
        self._handlers.clear()
        self.register_defaults()
    
    @abstractmethod
    def register_defaults(self) -> None:
        """Register default handlers. Subclasses must implement."""
        pass
    
    @abstractmethod
    def _invoke(self, name: str, context: Optional[Mapping[str, Any]], domain: str) -> Any:
        """Invoke a handler. Subclasses must implement.
        
        Args:
            name: Handler name
            context: Context dict to pass to handler
            domain: Domain for handler lookup
            
        Returns:
            Handler result
            
        Raises:
            ValueError: If handler not found
        """
        pass


class GuardRegistryBase(DomainRegistry[Callable[[Mapping[str, Any]], bool]]):
    """Base registry for guard functions that return bool."""
    
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
            domain: Domain for guard lookup
            
        Returns:
            Guard result (bool)
            
        Raises:
            ValueError: If guard not found
        """
        return self._invoke(name, context, domain)
    
    def _invoke(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> bool:
        handler = self.get(name, domain)
        if handler is None:
            raise ValueError(f"Unknown guard: {name} (domain: {domain})")
        ctx = context or {}
        return bool(handler(ctx))


class ConditionRegistryBase(DomainRegistry[Callable[[Mapping[str, Any]], bool]]):
    """Base registry for condition predicates that return bool."""
    
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
            domain: Domain for condition lookup
            
        Returns:
            Condition result (bool)
            
        Raises:
            ValueError: If condition not found
        """
        return self._invoke(name, context, domain)
    
    def _invoke(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> bool:
        handler = self.get(name, domain)
        if handler is None:
            raise ValueError(f"Unknown condition: {name} (domain: {domain})")
        ctx = context or {}
        return bool(handler(ctx))


class ActionRegistryBase(DomainRegistry[Callable[[Mapping[str, Any]], Any]]):
    """Base registry for action functions."""
    
    def execute(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> Any:
        """Execute an action.
        
        Args:
            name: Action name
            context: Context dict for action execution
            domain: Domain for action lookup
            
        Returns:
            Action result
            
        Raises:
            ValueError: If action not found
        """
        return self._invoke(name, context, domain)
    
    def _invoke(
        self, 
        name: str, 
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN
    ) -> Any:
        handler = self.get(name, domain)
        if handler is None:
            raise ValueError(f"Unknown action: {name} (domain: {domain})")
        ctx = context or {}
        return handler(ctx)


def _get_guard_registry() -> "GuardRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from .guards import registry
    return registry


def _get_action_registry() -> "ActionRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from .actions import registry
    return registry


def _get_condition_registry() -> "ConditionRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from .conditions import registry
    return registry


def register_guard(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register a guard function.
    
    Usage:
        @register_guard("can_start_task")
        def can_start_task(ctx: Mapping[str, Any]) -> bool:
            return ctx.get("task", {}).get("claimed", False)
    
    Args:
        name: Guard name to register
        domain: Optional domain for domain-specific guards
        
    Returns:
        Decorator that registers the function
    """
    def decorator(fn):
        _get_guard_registry().register(name, fn, domain)
        return fn
    return decorator


def register_action(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register an action function.
    
    Usage:
        @register_action("record_completion_time")
        def record_completion_time(ctx: MutableMapping[str, Any]) -> None:
            ctx["completed_at"] = time.time()
    
    Args:
        name: Action name to register
        domain: Optional domain for domain-specific actions
        
    Returns:
        Decorator that registers the function
    """
    def decorator(fn):
        _get_action_registry().register(name, fn, domain)
        return fn
    return decorator


def register_condition(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register a condition function.
    
    Usage:
        @register_condition("all_work_complete")
        def all_work_complete(ctx: Mapping[str, Any]) -> bool:
            return ctx.get("session", {}).get("work_complete", False)
    
    Args:
        name: Condition name to register
        domain: Optional domain for domain-specific conditions
        
    Returns:
        Decorator that registers the function
    """
    def decorator(fn):
        _get_condition_registry().register(name, fn, domain)
        return fn
    return decorator


__all__ = [
    "DomainRegistry",
    "GuardRegistryBase",
    "ConditionRegistryBase",
    "ActionRegistryBase",
    # Registration decorators
    "register_guard",
    "register_action",
    "register_condition",
]


