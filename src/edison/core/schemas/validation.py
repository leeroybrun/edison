"""Shared schema validation utilities.

This module provides centralized JSON schema loading and validation
for use across all Edison implementations.

Design principles:
- DRY: Single source of truth for schema operations
- NO MOCKS: Real jsonschema validation
- Fail-safe: Gracefully handles missing jsonschema library
- Path-aware: Uses bundled data for schemas (ALWAYS)

Architecture:
- Schemas are ALWAYS from bundled edison.data/schemas/
- NO .edison/core/schemas/ - that is legacy
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

from edison.core.utils.io import read_json

# jsonschema is an optional dependency without type stubs
# We define a protocol for type checking and handle runtime import gracefully
if TYPE_CHECKING:
    class ValidationError(Exception):
        """Protocol for jsonschema.ValidationError."""
        message: str
        path: List[Any]

    class Validator(Protocol):
        """Protocol for jsonschema validators."""
        def iter_errors(self, instance: Any) -> Any: ...

    class JsonSchemaModule(Protocol):
        """Protocol for jsonschema module."""
        def validate(self, instance: Any, schema: Dict[str, Any]) -> None: ...
        ValidationError: type[ValidationError]

    jsonschema: Optional[JsonSchemaModule]
    Draft202012Validator: Optional[type[Validator]]
else:
    try:
        import jsonschema
    except Exception:  # pragma: no cover - surfaced via doctor script
        jsonschema = None

    # Import validator for better error messages if available
    try:
        from jsonschema import Draft202012Validator  # type: ignore[import-not-found]
    except Exception:
        Draft202012Validator = None

from edison.data import get_data_path


class SchemaValidationError(ValueError):
    """Raised when schema validation fails."""

    pass


def _get_schemas_dir(repo_root: Optional[Path] = None) -> Path:
    """Resolve schemas directory.

    Schemas are ALWAYS from bundled edison.data package.
    NO .edison/core/schemas/ - that is legacy.

    Args:
        repo_root: Ignored (kept for API compatibility).

    Returns:
        Path to bundled schemas directory.

    Raises:
        FileNotFoundError: If schemas directory cannot be found.
    """
    # Schemas are ALWAYS from bundled data
    try:
        packaged_schemas = get_data_path("schemas")
        if packaged_schemas.exists():
            return packaged_schemas
    except Exception:
        pass

    raise FileNotFoundError(
        "Schemas directory not found in bundled edison.data package.\n"
        "Ensure edison is properly installed."
    )


def load_schema(schema_name: str, *, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load a JSON schema from the bundled schemas directory.

    Automatically appends .json extension if not present.

    Args:
        schema_name: Name of schema file (e.g., "claude-agent.schema.json"
            or "claude-agent.schema")
        repo_root: Ignored (kept for API compatibility).

    Returns:
        Parsed schema dictionary.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        json.JSONDecodeError: If schema is invalid JSON.
    """
    # Normalize schema name - add .json if missing
    if not schema_name.endswith(".json"):
        schema_name = f"{schema_name}.json"

    schemas_dir = _get_schemas_dir(repo_root)
    schema_path = schemas_dir / schema_name

    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema not found: {schema_name}\n"
            f"Looked in: {schemas_dir}"
        )

    try:
        return read_json(schema_path)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in schema {schema_name}: {e.msg}",
            e.doc,
            e.pos,
        ) from e


def validate_payload(
    payload: Dict[str, Any],
    schema_name: str,
    *,
    repo_root: Optional[Path] = None,
) -> None:
    """Validate a payload against a JSON schema.

    Args:
        payload: Data to validate.
        schema_name: Name of schema to validate against.
        repo_root: Ignored (kept for API compatibility).

    Raises:
        SchemaValidationError: If validation fails.
        FileNotFoundError: If schema doesn't exist.
        json.JSONDecodeError: If schema is invalid JSON.
    """
    if jsonschema is None:
        # jsonschema not available - skip validation
        return

    schema = load_schema(schema_name, repo_root=repo_root)

    try:
        jsonschema.validate(instance=payload, schema=schema)
    except Exception as exc:
        # Wrap jsonschema validation error in our custom error
        raise SchemaValidationError(
            f"Validation failed against schema '{schema_name}': {exc}"
        ) from exc


def validate_payload_safe(
    payload: Dict[str, Any],
    schema_name: str,
    *,
    repo_root: Optional[Path] = None,
) -> List[str]:
    """Validate a payload and return list of error messages (empty if valid).

    This is a safe variant that returns errors instead of raising exceptions,
    useful for collecting multiple validation errors.

    Args:
        payload: Data to validate.
        schema_name: Name of schema to validate against.
        repo_root: Ignored (kept for API compatibility).

    Returns:
        List of error messages. Empty list if validation passes.
    """
    if jsonschema is None:
        # jsonschema not available - return empty (no validation)
        return []

    try:
        schema = load_schema(schema_name, repo_root=repo_root)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Schema loading failed - return error message
        return [f"Schema loading failed: {e}"]

    errors: List[str] = []

    try:
        # Use Draft202012Validator for better error reporting if available
        if Draft202012Validator is not None:
            validator = Draft202012Validator(schema)

            for error in sorted(validator.iter_errors(payload), key=lambda e: str(e.path)):
                # Build a readable error message with path
                if hasattr(error, 'path') and error.path:
                    path_str = ".".join(str(p) for p in error.path)
                    errors.append(f"{path_str}: {error.message}")
                else:
                    errors.append(error.message)
        else:
            # Fallback to basic validation
            jsonschema.validate(instance=payload, schema=schema)

    except Exception as exc:
        # Catch validation errors
        if not errors:
            errors.append(str(exc))

    return errors


__all__ = [
    "load_schema",
    "validate_payload",
    "validate_payload_safe",
    "SchemaValidationError",
]
