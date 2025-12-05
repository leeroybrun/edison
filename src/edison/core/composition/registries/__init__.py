"""Content-type specific registries.

Provides composition registries for different content types.
Most content types use GenericRegistry via configuration.

Special registries:
- ConstitutionRegistry: Needs get_context_vars() for rules/reads injection
- RulesRegistry: Domain service for rules (moved to core/rules/registry.py)
- JsonSchemaRegistry: JSON schema composition

For entity metadata lookup, use core.registries instead:
- AgentRegistry: Agent metadata from frontmatter
- ValidatorRegistry: Validator roster from config

For rules, import from core.rules directly:
- from edison.core.rules import RulesRegistry
"""
from __future__ import annotations

from .constitutions import (
    ConstitutionRegistry,
    generate_all_constitutions,
)

from .file_patterns import (
    FilePatternRegistry,
)
from .schemas import (
    JsonSchemaRegistry,
)
from .generic import GenericRegistry
from ._base import ComposableRegistry
from ._types_manager import ComposableTypesManager
from ..core.errors import (
    AnchorNotFoundError,
    RulesCompositionError,
)

# Note: RulesRegistry has been moved to core/rules/registry.py
# Import directly from there: from edison.core.rules import RulesRegistry

__all__ = [
    # Constitutions
    "ConstitutionRegistry",
    "generate_all_constitutions",
    # File patterns and schemas
    "FilePatternRegistry",
    "JsonSchemaRegistry",
    # Generic
    "GenericRegistry",
    # Base classes
    "ComposableRegistry",
    "ComposableTypesManager",
    # Errors
    "AnchorNotFoundError",
    "RulesCompositionError",
]
