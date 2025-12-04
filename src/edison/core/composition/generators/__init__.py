"""Generators module for data-driven document generation.

Two-phase generation:
1. Compose template from layers (MarkdownCompositionStrategy)
2. Inject data (TemplateEngine with {{#each}} loops)

All generators extend ComposableGenerator.
"""
from __future__ import annotations

from .base import ComposableGenerator
from .roster import AgentRosterGenerator, ValidatorRosterGenerator
from .state_machine import StateMachineGenerator
from .roots import generate_root_entry, generate_canonical_entry

__all__ = [
    "AgentRosterGenerator",
    "ComposableGenerator",
    "StateMachineGenerator",
    "ValidatorRosterGenerator",
    # Root entry generators
    "generate_root_entry",
    "generate_canonical_entry",  # Backward-compatible alias
]
