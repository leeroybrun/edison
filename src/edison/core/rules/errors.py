"""
Exception classes for the Edison Rules system.

This module defines all exceptions raised by the rules engine,
registry, and composition systems.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RuleViolation


class AnchorNotFoundError(KeyError):
    """Raised when a referenced guideline anchor cannot be found."""

    pass


class RulesCompositionError(RuntimeError):
    """Raised when rule registry loading or composition fails."""

    pass


class RuleViolationError(Exception):
    """Raised when a blocking rule is violated."""

    def __init__(self, message: str, violations: list[RuleViolation]):
        super().__init__(message)
        self.violations = violations


__all__ = [
    "AnchorNotFoundError",
    "RulesCompositionError",
    "RuleViolationError",
]
