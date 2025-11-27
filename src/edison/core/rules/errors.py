"""
Exception classes for the Edison Rules system (runtime).

This module defines runtime exceptions raised by the rules engine.

Note: Composition errors (AnchorNotFoundError, RulesCompositionError) have been
moved to edison.core.composition.core.errors for architectural coherence.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RuleViolation


class RuleViolationError(Exception):
    """Raised when a blocking rule is violated."""

    def __init__(self, message: str, violations: list[RuleViolation]):
        super().__init__(message)
        self.violations = violations


__all__ = [
    "RuleViolationError",
]
