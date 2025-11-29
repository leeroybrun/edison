"""
Edison Rules Engine and Rules Composition.

This module contains two related systems:

1. RulesRegistry / compose_rules (in composition.registries.rules):
   - Load rule metadata from YAML registries (core + packs)
   - Resolve guideline anchors (<!-- ANCHOR: name --> ... <!-- END ANCHOR: name -->)
   - Apply include resolution via the composition engine
   - Produce a composed, machine-readable rules view for CLIs and tooling

2. RulesEngine (in this module):
   - Enforce per-project rules at task state transitions based on project config overlays

Composition components have been moved to composition.registries for architectural
coherence. This module re-exports them for convenience.
"""
from __future__ import annotations

# Runtime enforcement (stays in this module)
from .errors import RuleViolationError
from .models import Rule, RuleViolation
from .engine import RulesEngine
from .checker import get_rules_for_context_formatted, format_rules_output

# Composition components (re-exported from new locations)
from edison.core.composition.registries.rules import (
    RulesRegistry,
    compose_rules,
    extract_anchor_content,
    load_bundled_rules,
    get_rules_for_role,
    filter_rules,
)
from edison.core.composition.registries.file_patterns import FilePatternRegistry
from edison.core.composition.core.errors import (
    AnchorNotFoundError,
    RulesCompositionError,
)

# Re-export all public symbols
__all__ = [
    # Exceptions
    "AnchorNotFoundError",
    "RulesCompositionError",
    "RuleViolationError",
    # Models
    "Rule",
    "RuleViolation",
    # Registry (composition)
    "RulesRegistry",
    "compose_rules",
    "extract_anchor_content",
    "load_bundled_rules",
    "get_rules_for_role",
    "filter_rules",
    "FilePatternRegistry",
    # Engine (runtime)
    "RulesEngine",
    # Checker (runtime)
    "get_rules_for_context_formatted",
    "format_rules_output",
]
