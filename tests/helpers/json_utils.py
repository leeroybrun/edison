"""JSON traversal utilities for test helpers.

Consolidates JSON field access and traversal logic used in assertions.
"""
from __future__ import annotations

from typing import Any, Dict


def traverse_json_path(data: Dict[str, Any], field: str) -> Any:
    """Traverse a JSON path using dot notation.

    Args:
        data: JSON data dict
        field: Field path (supports dot notation for nested fields)

    Returns:
        Value at the field path

    Raises:
        KeyError: If any part of the path is not found
    """
    current = data
    parts = field.split(".")

    for i, part in enumerate(parts):
        if part not in current:
            path = ".".join(parts[:i+1])
            raise KeyError(f"Field path '{path}' not found in JSON data")
        current = current[part]

    return current


def has_json_field(data: Dict[str, Any], field: str) -> bool:
    """Check if a JSON path exists using dot notation.

    Args:
        data: JSON data dict
        field: Field path (supports dot notation for nested fields)

    Returns:
        True if the field path exists
    """
    try:
        traverse_json_path(data, field)
        return True
    except KeyError:
        return False


def get_json_field(data: Dict[str, Any], field: str, default: Any = None) -> Any:
    """Get a JSON field value with a default fallback.

    Args:
        data: JSON data dict
        field: Field path (supports dot notation for nested fields)
        default: Default value if field not found

    Returns:
        Value at the field path, or default if not found
    """
    try:
        return traverse_json_path(data, field)
    except KeyError:
        return default
