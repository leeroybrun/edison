"""Generic domain-aware registries for state machine handlers.

This module provides base registry classes that support domain-prefixed lookups,
allowing the same handler names to be registered with different implementations
per domain (task, session, qa, etc.).

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
        """Create registry key from name and domain."""
        if domain == self.SHARED_DOMAIN:
            return name
        return f"{domain}:{name}"

    def register(self, name: str, handler: T, domain: str = SHARED_DOMAIN) -> None:
        """Register a handler function."""
        if not callable(handler):
            raise TypeError("handler must be callable")
        key = self._make_key(name, domain)
        self._handlers[key] = handler

    def add(self, name: str, handler: T, domain: str = SHARED_DOMAIN) -> None:
        """Add a handler function (alias for register)."""
        self.register(name, handler, domain)

    def get(self, name: str, domain: str = SHARED_DOMAIN) -> Optional[T]:
        """Get a handler by name, with domain fallback."""
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
        """Check if a handler exists."""
        return self.get(name, domain) is not None

    def list_handlers(self, domain: Optional[str] = None) -> Dict[str, T]:
        """List all handlers, optionally filtered by domain."""
        if domain is None:
            return dict(self._handlers)

        result: Dict[str, T] = {}
        prefix = f"{domain}:"

        for key, handler in self._handlers.items():
            if key.startswith(prefix):
                # Domain-specific handler
                name = key[len(prefix) :]
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

    @abstractmethod
    def _invoke(self, name: str, context: Optional[Mapping[str, Any]], domain: str) -> Any:
        """Invoke a handler. Subclasses must implement."""


class GuardRegistryBase(DomainRegistry[Callable[[Mapping[str, Any]], bool]]):
    """Base registry for guard functions that return bool."""

    def check(
        self,
        name: str,
        context: Optional[Mapping[str, Any]] = None,
        domain: str = DomainRegistry.SHARED_DOMAIN,
    ) -> bool:
        """Check a guard condition."""
        return self._invoke(name, context, domain)

    def _invoke(
        self,
        name: str,
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN,
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
        domain: str = DomainRegistry.SHARED_DOMAIN,
    ) -> bool:
        """Check a condition."""
        return self._invoke(name, context, domain)

    def _invoke(
        self,
        name: str,
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN,
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
        domain: str = DomainRegistry.SHARED_DOMAIN,
    ) -> Any:
        """Execute an action."""
        return self._invoke(name, context, domain)

    def _invoke(
        self,
        name: str,
        context: Optional[Mapping[str, Any]],
        domain: str = DomainRegistry.SHARED_DOMAIN,
    ) -> Any:
        handler = self.get(name, domain)
        if handler is None:
            raise ValueError(f"Unknown action: {name} (domain: {domain})")
        ctx = context or {}
        return handler(ctx)


def _get_guard_registry() -> "GuardRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from ..guards import registry

    return registry


def _get_action_registry() -> "ActionRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from ..actions import registry

    return registry


def _get_condition_registry() -> "ConditionRegistryBase":
    """Lazy import to avoid circular dependencies."""
    from ..conditions import registry

    return registry


def register_guard(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register a guard function."""

    def decorator(fn):
        _get_guard_registry().register(name, fn, domain)
        return fn

    return decorator


def register_action(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register an action function."""

    def decorator(fn):
        _get_action_registry().register(name, fn, domain)
        return fn

    return decorator


def register_condition(name: str, domain: str = DomainRegistry.SHARED_DOMAIN):
    """Decorator to register a condition function."""

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
