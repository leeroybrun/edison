"""
Edison Rules Engine and Rules Composition.

This module contains two related systems:

1. RulesRegistry / compose_rules:
   - Load rule metadata from YAML registries (core + packs)
   - Resolve guideline anchors (<!-- ANCHOR: name --> ... <!-- END ANCHOR: name -->)
   - Apply include resolution via the composition engine
   - Produce a composed, machine-readable rules view for CLIs and tooling

2. RulesEngine:
   - Enforce per-project rules at task state transitions based on project config overlays

This package is split into focused modules:
  - errors: Exception classes (AnchorNotFoundError, RulesCompositionError, RuleViolationError)
  - models: Data models (Rule, RuleViolation)
  - helpers: Utility functions (extract_anchor_content)
  - registry: RulesRegistry class for loading and composing rules
  - engine: RulesEngine class for enforcing rules at runtime
"""
from __future__ import annotations

# Import all public symbols from submodules
from .errors import (
    AnchorNotFoundError,
    RulesCompositionError,
    RuleViolationError,
)
from .models import (
    Rule,
    RuleViolation,
)
from .registry import (
    RulesRegistry,
    compose_rules,
)
from .file_patterns import FilePatternRegistry
from .engine import (
    RulesEngine,
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
    # Registry
    "RulesRegistry",
    "compose_rules",
    "FilePatternRegistry",
    # Engine
    "RulesEngine",
]
