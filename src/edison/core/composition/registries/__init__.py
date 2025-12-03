"""Content-type specific registries.

Each registry provides discovery, composition, and metadata access
for a specific content type (agents, validators, guidelines, constitutions, rules).
"""
from __future__ import annotations

from .agents import (
    AgentRegistry,
    AgentError,
    AgentNotFoundError,
    compose_agent,
)
from .validators import (
    ValidatorRegistry,
    collect_validators,
    infer_validator_metadata,
    normalize_validator_entries,
)
from .guidelines import (
    GuidelineRegistry,
    GuidelineCompositionResult,
    GuidelinePaths,
    compose_guideline,
)
from .constitutions import (
    ConstitutionRegistry,
    ConstitutionResult,
    generate_all_constitutions,
)
# Note: Rosters (generate_available_agents, generate_available_validators)
# have been moved to composition/generators/
# generate_canonical_entry is still defined here for now

from .rules import (
    RulesRegistry,
    compose_rules,
    extract_anchor_content,
    load_bundled_rules,
    get_rules_for_role as get_rules_for_role_api,
    filter_rules,
)
from .file_patterns import (
    FilePatternRegistry,
)
from .schemas import (
    JsonSchemaComposer,
)
from .documents import (
    DocumentTemplateRegistry,
    DocumentTemplateError,
    DocumentTemplateNotFoundError,
    DocumentTemplate,
    compose_document,
)
from ..core.errors import (
    AnchorNotFoundError,
    RulesCompositionError,
)

__all__ = [
    # Agents
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "compose_agent",
    # Validators
    "ValidatorRegistry",
    "collect_validators",
    "infer_validator_metadata",
    "normalize_validator_entries",
    # Guidelines
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    # Constitutions
    "ConstitutionRegistry",
    "ConstitutionResult",
    "generate_all_constitutions",
    # Rosters (generate_canonical_entry still available if rosters.py exists)
    "generate_canonical_entry",
    # Rules
    "RulesRegistry",
    "compose_rules",
    "extract_anchor_content",
    "load_bundled_rules",
    "get_rules_for_role_api",
    "filter_rules",
    "FilePatternRegistry",
    "JsonSchemaComposer",
    # Documents
    "DocumentTemplateRegistry",
    "DocumentTemplateError",
    "DocumentTemplateNotFoundError",
    "DocumentTemplate",
    "compose_document",
    # Errors
    "AnchorNotFoundError",
    "RulesCompositionError",
]
