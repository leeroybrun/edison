"""Single-file data-driven document generators.

Unlike registries (which discover and compose multiple files),
generators produce single data-driven documents using templates
with {{#each}} loop expansion.

All generators extend ComposableRegistry (from registries.base) and 
override get_context_vars() to provide data for template substitution.

Available generators:
- AgentRosterGenerator: AVAILABLE_AGENTS.md
- ValidatorRosterGenerator: AVAILABLE_VALIDATORS.md  
- StateMachineGenerator: STATE_MACHINE.md

Note: The old ComposableGenerator base class has been removed.
All generators now use ComposableRegistry directly.
"""
from __future__ import annotations

from .available_agents import AgentRosterGenerator
from .available_validators import ValidatorRosterGenerator
from .state_machine import StateMachineGenerator

__all__ = [
    "AgentRosterGenerator",
    "ValidatorRosterGenerator",
    "StateMachineGenerator",
]
