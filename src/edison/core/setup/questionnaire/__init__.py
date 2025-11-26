"""Setup questionnaire package for Edison framework.

This package splits the questionnaire functionality into focused modules:
- base: Main SetupQuestionnaire class and workflow
- prompts: User prompting and default value resolution
- validation: Input validation and type coercion
- rendering: Template rendering and config generation

Public API exports maintain backward compatibility with existing code.
"""
from __future__ import annotations

# Main class for backward compatibility
from .base import SetupQuestionnaire

# Sub-modules available for internal use
from . import prompts
from . import validation
from . import rendering
from . import context
from . import templates

__all__ = [
    "SetupQuestionnaire",
    "prompts",
    "validation",
    "rendering",
    "context",
    "templates",
]
