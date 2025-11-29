"""Utility classes for orchestrator configuration and templating."""

from __future__ import annotations


class SafeDict(dict):
    """
    Dictionary subclass that preserves unknown placeholders in format strings.

    When used with str.format_map(), unknown placeholders are preserved
    instead of raising KeyError. This is useful for templating where some
    placeholders may be optional or conditionally available.

    Examples:
        >>> tokens = SafeDict({"name": "Alice", "age": "30"})
        >>> "Hello {name}, ID: {id}".format_map(tokens)
        'Hello Alice, ID: {id}'

        >>> # Known placeholders are substituted
        >>> "Hello {name}, you are {age} years old".format_map(tokens)
        'Hello Alice, you are 30 years old'

        >>> # Unknown placeholders are preserved
        >>> "System: {system}, User: {user}".format_map(SafeDict())
        'System: {system}, User: {user}'
    """

    def __missing__(self, key: str) -> str:
        """
        Return placeholder string for missing keys instead of raising KeyError.

        Args:
            key: The missing dictionary key

        Returns:
            The key wrapped in curly braces (e.g., "{key}")
        """
        return "{" + key + "}"


__all__ = ["SafeDict"]
