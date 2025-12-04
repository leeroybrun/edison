"""Content-type specific registries.

Provides composition registries for different content types.
Most content types use GenericRegistry via configuration.

Special registries:
- ConstitutionRegistry: Needs get_context_vars() for rules/reads injection
- RulesRegistry: Domain service for rules (moved to core/rules/registry.py)
- JsonSchemaComposer: JSON schema composition

For entity metadata lookup, use core.registries instead:
- AgentRegistry: Agent metadata from frontmatter
- ValidatorRegistry: Validator roster from config

For rules, import from core.rules directly:
- from edison.core.rules import RulesRegistry
"""
from __future__ import annotations

from .constitutions import (
    ConstitutionRegistry,
    ConstitutionResult,
    generate_all_constitutions,
)

from .file_patterns import (
    FilePatternRegistry,
)
from .schemas import (
    JsonSchemaRegistry,
    JsonSchemaComposer,  # Legacy alias
)
from .generic import GenericRegistry
from ._registry_base import BaseRegistry
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
    "ConstitutionResult",
    "generate_all_constitutions",
    # File patterns and schemas
    "FilePatternRegistry",
    "JsonSchemaComposer",
    # Generic
    "GenericRegistry",
    # Base classes (internal - use underscore prefix files)
    "BaseRegistry",
    "ComposableRegistry",
    "ComposableTypesManager",
    # Errors
    "AnchorNotFoundError",
    "RulesCompositionError",
]
