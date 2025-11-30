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


def create_session_json(
    session_id: str,
    owner: str = "test",
    state: str = "draft",
) -> dict:
    """Create session JSON structure.

    Args:
        session_id: Session identifier
        owner: Session owner
        state: Session state

    Returns:
        Dict with session structure
    """
    return {
        "meta": {
            "sessionId": session_id,
            "owner": owner,
            "status": state,
        },
        "state": state,
        "tasks": {},
        "qa": {},
    }


def get_session_field(session_data: dict, field_path: str) -> Any:
    """Get field from session JSON with dot notation.

    Args:
        session_data: Session JSON dict
        field_path: Dot-separated path (e.g., "meta.sessionId")

    Returns:
        Value at path or None if not found

    Example:
        session_id = get_session_field(data, "meta.sessionId")
    """
    parts = field_path.split(".")
    value = session_data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value
