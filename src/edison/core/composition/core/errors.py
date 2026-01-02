"""Unified composition error hierarchy.

Provides structured error classes for all composition operations:
- Validation errors (entity not found, shadowing, section issues)
- Template errors (include not found, condition syntax)
- Output errors (file write, path resolution)
- Registry errors (rules, schema loading)

All errors inherit from CompositionError for easy catching.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence


# =============================================================================
# Base Error Class
# =============================================================================


class CompositionError(Exception):
    """Base class for all composition errors.

    All composition-related errors should inherit from this class
    to enable unified error handling.
    """

    pass


# =============================================================================
# Validation Errors
# =============================================================================


class CompositionValidationError(CompositionError):
    """Raised when composition validation fails.

    Parent class for validation-specific errors.
    """

    pass


class CompositionNotFoundError(CompositionValidationError):
    """Raised when a requested entity is not found.

    Attributes:
        entity_name: Name of the missing entity.
        entity_type: Type of entity (agent, guideline, etc.).
        available: List of available entities.
    """

    def __init__(
        self,
        entity_name: str,
        entity_type: str = "entity",
        available: Optional[Sequence[str]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.entity_name = entity_name
        self.entity_type = entity_type
        self.available = list(available) if available else []

        if message:
            super().__init__(message)
        else:
            msg = f"{entity_type.title()} '{entity_name}' not found."
            if self.available:
                msg += f" Available: {sorted(self.available)}"
            super().__init__(msg)


class CompositionShadowingError(CompositionValidationError):
    """Raised when a new entity shadows an existing one.

    Attributes:
        entity_name: Name of the shadowing entity.
        shadow_layer: Layer attempting to shadow.
        original_layer: Layer that originally defined the entity.
    """

    def __init__(
        self,
        entity_name: str,
        shadow_layer: str = "unknown",
        original_layer: str = "core",
        message: Optional[str] = None,
    ) -> None:
        self.entity_name = entity_name
        self.shadow_layer = shadow_layer
        self.original_layer = original_layer

        if message:
            super().__init__(message)
        else:
            super().__init__(
                f"Entity '{entity_name}' in {shadow_layer} shadows existing "
                f"entity in {original_layer}. Use overlays/ for extensions."
            )


class CompositionSectionError(CompositionValidationError):
    """Raised when section handling fails.

    Attributes:
        section_name: Name of the problematic section.
        reason: Reason for the failure.
    """

    def __init__(
        self,
        section_name: str,
        reason: str = "unknown error",
        message: Optional[str] = None,
    ) -> None:
        self.section_name = section_name
        self.reason = reason

        if message:
            super().__init__(message)
        else:
            super().__init__(f"Section '{section_name}': {reason}")


# =============================================================================
# Template Errors
# =============================================================================


class TemplateError(CompositionError):
    """Base class for template processing errors."""

    pass


class IncludeNotFoundError(TemplateError):
    """Raised when an include cannot be resolved.

    Attributes:
        include_path: Path that couldn't be resolved.
        search_locations: Locations that were searched.
    """

    def __init__(
        self,
        include_path: str,
        search_locations: Optional[Sequence[Path]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.include_path = include_path
        self.search_locations = list(search_locations) if search_locations else []

        if message:
            super().__init__(message)
        else:
            msg = f"Include not found: {include_path}"
            if self.search_locations:
                locations = [str(p) for p in self.search_locations]
                msg += f" (searched: {locations})"
            super().__init__(msg)


class ConditionSyntaxError(TemplateError):
    """Raised when condition syntax is invalid.

    Attributes:
        expression: The invalid expression.
        reason: Why it's invalid.
    """

    def __init__(
        self,
        expression: str,
        reason: str = "invalid syntax",
        message: Optional[str] = None,
    ) -> None:
        self.expression = expression
        self.reason = reason

        if message:
            super().__init__(message)
        else:
            super().__init__(f"Invalid condition '{expression}': {reason}")


class CircularIncludeError(TemplateError):
    """Raised when circular includes are detected.

    Attributes:
        include_path: Path that caused the cycle.
        include_chain: Chain of includes leading to the cycle.
    """

    def __init__(
        self,
        include_path: str,
        include_chain: Optional[Sequence[str]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.include_path = include_path
        self.include_chain = list(include_chain) if include_chain else []

        if message:
            super().__init__(message)
        else:
            chain_str = " → ".join(self.include_chain + [include_path])
            super().__init__(f"Circular include detected: {chain_str}")


# =============================================================================
# Output Errors
# =============================================================================


class OutputError(CompositionError):
    """Base class for output-related errors."""

    pass


class OutputWriteError(OutputError):
    """Raised when writing output fails.

    Attributes:
        output_path: Path that couldn't be written.
        reason: Reason for the failure.
    """

    def __init__(
        self,
        output_path: Path,
        reason: str = "unknown error",
        message: Optional[str] = None,
    ) -> None:
        self.output_path = output_path
        self.reason = reason

        if message:
            super().__init__(message)
        else:
            super().__init__(f"Failed to write {output_path}: {reason}")


class PathResolutionError(OutputError):
    """Raised when path resolution fails.

    Attributes:
        path_template: Template that couldn't be resolved.
        missing_vars: Variables that were missing.
    """

    def __init__(
        self,
        path_template: str,
        missing_vars: Optional[Sequence[str]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.path_template = path_template
        self.missing_vars = list(missing_vars) if missing_vars else []

        if message:
            super().__init__(message)
        else:
            msg = f"Failed to resolve path: {path_template}"
            if self.missing_vars:
                msg += f" (missing: {self.missing_vars})"
            super().__init__(msg)


# =============================================================================
# Registry Errors
# =============================================================================


class RegistryError(CompositionError):
    """Base class for registry-related errors."""

    pass


class RulesCompositionError(RuntimeError, RegistryError):
    """Raised when rule registry loading or composition fails."""

    pass


class SchemaLoadError(RegistryError):
    """Raised when JSON schema loading fails.

    Attributes:
        schema_name: Name of the schema that failed.
        reason: Reason for the failure.
    """

    def __init__(
        self,
        schema_name: str,
        reason: str = "unknown error",
        message: Optional[str] = None,
    ) -> None:
        self.schema_name = schema_name
        self.reason = reason

        if message:
            super().__init__(message)
        else:
            super().__init__(f"Failed to load schema '{schema_name}': {reason}")


# =============================================================================
# Anchor/Section Lookup Errors (Backward Compatibility)
# =============================================================================


class AnchorNotFoundError(KeyError, CompositionError):
    """Raised when a referenced guideline anchor cannot be found.

    Kept for backward compatibility with existing code.
    """

    pass


class SectionNotFoundError(KeyError, CompositionError):
    """Raised when a referenced section cannot be found.

    Attributes:
        section_name: Name of the missing section.
        file_path: File where the section was expected.
    """

    def __init__(
        self,
        section_name: str,
        file_path: Optional[Path] = None,
        message: Optional[str] = None,
    ) -> None:
        self.section_name = section_name
        self.file_path = file_path

        if message:
            msg = message
        else:
            msg = f"Section '{section_name}' not found"
            if file_path:
                msg += f" in {file_path}"

        super().__init__(msg)
