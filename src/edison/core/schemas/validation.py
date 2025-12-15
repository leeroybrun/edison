"""Shared schema validation utilities.

Edison validates structured YAML frontmatter payloads using JSON Schema.
Schemas are stored as YAML files (human-readable + easy to override/compose),
and loaded in a single, consistent way across the codebase.

Schema resolution order (highest priority → lowest):
1) Project-composed schemas: ``.edison/_generated/schemas/`` (core + packs + project)
2) Bundled defaults: ``edison.data/schemas/`` (core only)

This lets pack/project overlays actually affect runtime validation while keeping
a safe fallback when composed output is unavailable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

from edison.core.utils.io import read_yaml
from edison.core.utils.paths import get_project_config_dir

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


def _iter_schema_dirs(repo_root: Optional[Path] = None) -> List[Path]:
    """Return schema search roots in priority order."""
    roots: List[Path] = []

    if repo_root is not None:
        try:
            project_dir = get_project_config_dir(repo_root, create=False)
            roots.append(project_dir / "_generated" / "schemas")
        except Exception:
            pass

    try:
        roots.append(get_data_path("schemas"))
    except Exception:
        pass

    return roots


def _get_schemas_dir(repo_root: Optional[Path] = None) -> Path:
    """Back-compat helper: prefer project-composed schemas dir when present."""
    for candidate in _iter_schema_dirs(repo_root):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No schemas directory found (project or bundled).")


def load_schema(schema_name: str, *, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load a schema dict from composed or bundled schema directories.

    Canonical schema serialization format is YAML (JSON Schema expressed in YAML).
    Automatically appends ``.yaml`` if no extension is present.

    Args:
        schema_name: Relative schema file path under schemas root
            (e.g., "reports/validator-report.schema.yaml" or "config/config.schema").
        repo_root: Repository root (enables project-composed schema overrides).

    Returns:
        Parsed schema dictionary.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
        ValueError: If schema is not a YAML mapping.
    """
    lowered = schema_name.lower()
    if lowered.endswith(".json"):
        raise ValueError(
            f"JSON schemas are no longer supported: {schema_name}. "
            "Use YAML schemas (e.g., *.schema.yaml)."
        )

    # Normalize schema name - add .yaml if missing
    if not (lowered.endswith(".yaml") or lowered.endswith(".yml")):
        schema_name = f"{schema_name}.yaml"

    schema_path: Optional[Path] = None
    for schemas_dir in _iter_schema_dirs(repo_root):
        candidate = schemas_dir / schema_name
        if candidate.exists():
            schema_path = candidate
            break

    if schema_path is None:
        searched = "\n".join(f"- {p}" for p in _iter_schema_dirs(repo_root))
        raise FileNotFoundError(f"Schema not found: {schema_name}\nSearched:\n{searched}")

    schema = read_yaml(schema_path, default=None, raise_on_error=True)
    if not isinstance(schema, dict):
        raise ValueError(f"Schema must be a YAML mapping, got {type(schema).__name__}")
    return schema


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
    except Exception as e:
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
