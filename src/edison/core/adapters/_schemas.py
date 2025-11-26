"""Shared schema validation utilities for adapters.

This module provides centralized JSON schema loading and validation
for use across all adapter implementations (Claude, Cursor, Zen, Codex).

Design principles:
- DRY: Single source of truth for schema operations
- NO MOCKS: Real jsonschema validation
- Fail-safe: Gracefully handles missing jsonschema library
- Path-aware: Uses PathResolver for consistent path resolution
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..file_io.utils import read_json_safe

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover - surfaced via doctor script
    jsonschema = None  # type: ignore[assignment]

from ..paths import PathResolver
from ..paths.project import get_project_config_dir


class SchemaValidationError(ValueError):
    """Raised when schema validation fails."""

    pass


def _get_schemas_dir(repo_root: Optional[Path] = None) -> Path:
    """Resolve schemas directory for the given repository root.

    Lookup order:
    1. <project_config_dir>/core/schemas (dev mode)
    2. src/edison/data/schemas (packaged mode)

    Args:
        repo_root: Optional repository root. If None, auto-detects.

    Returns:
        Path to schemas directory.

    Raises:
        FileNotFoundError: If schemas directory cannot be found.
    """
    if repo_root is None:
        repo_root = PathResolver.resolve_project_root()

    # Try dev mode location first
    config_dir = get_project_config_dir(repo_root, create=False)
    dev_schemas = config_dir / "core" / "schemas"
    if dev_schemas.exists():
        return dev_schemas

    # Try packaged data location
    try:
        from edison.data import get_data_path
        packaged_schemas = get_data_path("schemas")
        if packaged_schemas.exists():
            return packaged_schemas
    except Exception:
        pass

    # Fallback to src/edison/data/schemas for development
    src_schemas = repo_root / "src" / "edison" / "data" / "schemas"
    if src_schemas.exists():
        return src_schemas

    raise FileNotFoundError(
        f"Schemas directory not found. Tried:\n"
        f"  - {dev_schemas}\n"
        f"  - {src_schemas}"
    )


def load_schema(schema_name: str, *, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load a JSON schema from the schemas directory.

    Automatically appends .json extension if not present.

    Args:
        schema_name: Name of schema file (e.g., "claude-agent.schema.json"
            or "claude-agent.schema")
        repo_root: Optional repository root. If None, auto-detects.

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
        return read_json_safe(schema_path)
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
        repo_root: Optional repository root. If None, auto-detects.

    Raises:
        SchemaValidationError: If validation fails.
        FileNotFoundError: If schema doesn't exist.
        json.JSONDecodeError: If schema is invalid JSON.
    """
    if jsonschema is None:  # type: ignore[truthy-function]
        # jsonschema not available - skip validation
        return

    schema = load_schema(schema_name, repo_root=repo_root)

    try:
        jsonschema.validate(instance=payload, schema=schema)  # type: ignore[no-untyped-call]
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
        repo_root: Optional repository root. If None, auto-detects.

    Returns:
        List of error messages. Empty list if validation passes.
    """
    if jsonschema is None:  # type: ignore[truthy-function]
        # jsonschema not available - return empty (no validation)
        return []

    try:
        schema = load_schema(schema_name, repo_root=repo_root)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Schema loading failed - return error message
        return [f"Schema loading failed: {e}"]

    errors: List[str] = []

    try:
        # Use Draft202012Validator for better error reporting
        from jsonschema import Draft202012Validator  # type: ignore

        validator = Draft202012Validator(schema)  # type: ignore[no-untyped-call]

        for error in sorted(validator.iter_errors(payload), key=lambda e: str(e.path)):  # type: ignore[no-untyped-call]
            # Build a readable error message with path
            if error.path:  # type: ignore[attr-defined]
                path_str = ".".join(str(p) for p in error.path)  # type: ignore[attr-defined]
                errors.append(f"{path_str}: {error.message}")  # type: ignore[attr-defined]
            else:
                errors.append(error.message)  # type: ignore[attr-defined]

    except Exception as exc:
        # Fallback to basic validation
        try:
            jsonschema.validate(instance=payload, schema=schema)  # type: ignore[no-untyped-call]
        except Exception as e:
            errors.append(str(e))

    return errors


__all__ = [
    "load_schema",
    "validate_payload",
    "validate_payload_safe",
    "SchemaValidationError",
]
