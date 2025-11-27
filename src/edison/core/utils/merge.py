"""Canonical deep merge utilities.

This module provides the single source of truth for dictionary merging
throughout the Edison codebase. All other implementations should import
from here to avoid duplication.

Features:
- Recursive dictionary merging
- Smart array merging with override semantics:
  - Default: replace array entirely
  - Prefix with "+": append to existing array
  - Prefix with "=": explicit replace (same as default)
"""
from __future__ import annotations

from typing import Any, Dict, List


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dictionaries without mutating inputs.

    Args:
        base: Base dictionary (lower priority)
        override: Override dictionary (higher priority)

    Returns:
        New merged dictionary

    Example:
        >>> base = {"a": 1, "b": {"c": 2}}
        >>> override = {"b": {"d": 3}}
        >>> deep_merge(base, override)
        {'a': 1, 'b': {'c': 2, 'd': 3}}
    """
    result: Dict[str, Any] = dict(base)
    for key, value in (override or {}).items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = merge_arrays(result[key], value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def merge_arrays(base: List[Any], override: List[Any]) -> List[Any]:
    """Merge arrays with override semantics.

    Supports special prefixes in the first element:
    - "+" : Append override items (excluding prefix) to base
    - "=" : Replace base with override items (excluding prefix)
    - No prefix: Replace base entirely with override

    Args:
        base: Base list
        override: Override list

    Returns:
        Merged list

    Example:
        >>> merge_arrays([1, 2], [3, 4])
        [3, 4]
        >>> merge_arrays([1, 2], ["+", 3, 4])
        [1, 2, 3, 4]
        >>> merge_arrays([1, 2], ["=", 3, 4])
        [3, 4]
    """
    if not override:
        return base
    first = override[0]
    if isinstance(first, str):
        if first.startswith("+"):
            # Append mode: concat base with rest of override
            return [*base, *override[1:]]
        if first == "=":
            # Explicit replace: take rest of override
            return list(override[1:])
    # Default: replace entirely
    return list(override)


__all__ = ["deep_merge", "merge_arrays"]



