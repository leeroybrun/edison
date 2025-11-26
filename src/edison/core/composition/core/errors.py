"""Composition error classes."""
from __future__ import annotations


class CompositionValidationError(Exception):
    """Raised when composition validation fails."""
    pass


class CompositionNotFoundError(CompositionValidationError):
    """Raised when a requested entity is not found."""
    pass


class CompositionShadowingError(CompositionValidationError):
    """Raised when a new entity shadows an existing one."""
    pass


class CompositionSectionError(CompositionValidationError):
    """Raised when section handling fails."""
    pass
