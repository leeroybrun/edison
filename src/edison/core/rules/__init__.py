"""
Edison Rules Engine and Rules Composition.

This module contains two related systems:

1. RulesRegistry / compose_rules (in registry.py):
   - Load rule metadata from YAML registries (core + packs)
   - Resolve guideline anchors (<!-- ANCHOR: name --> ... <!-- END ANCHOR: name -->)
   - Apply include resolution via the composition engine
   - Produce a composed, machine-readable rules view for CLIs and tooling

2. RulesEngine (in engine.py):
   - Enforce per-project rules at task state transitions based on project config overlays
"""
from __future__ import annotations

# Runtime enforcement (stays in this module)
from .errors import RuleViolationError
from .models import Rule, RuleViolation
from .engine import RulesEngine
from .checker import get_rules_for_context_formatted, format_rules_output

# Composition components (now in registry.py)
from .registry import (
    RulesRegistry,
    compose_rules,
    get_rules_for_role,
    filter_rules,
)

# Re-export all public symbols
__all__ = [
    # Exceptions
    "RuleViolationError",
    # Models
    "Rule",
    "RuleViolation",
    # Registry (composition)
    "RulesRegistry",
    "compose_rules",
    "get_rules_for_role",
    "filter_rules",
    # Engine (runtime)
    "RulesEngine",
    # Checker (runtime)
    "get_rules_for_context_formatted",
    "format_rules_output",
]
