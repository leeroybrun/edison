"""Content-type specific registries.

Each registry provides discovery, composition, and metadata access
for a specific content type (agents, validators, guidelines, constitutions, rules).
"""
from __future__ import annotations

from .agents import (
    AgentRegistry,
    AgentError,
    AgentNotFoundError,
    AgentTemplateError,
    CoreAgent,
    PackOverlay,
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
    get_rules_for_role,
    load_constitution_layer,
    compose_constitution,
    render_constitution_template,
    generate_all_constitutions,
)
from .rosters import (
    generate_available_agents,
    generate_available_validators,
)
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
from ..core.errors import (
    AnchorNotFoundError,
    RulesCompositionError,
)

__all__ = [
    # Agents
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "AgentTemplateError",
    "CoreAgent",
    "PackOverlay",
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
    "get_rules_for_role",
    "load_constitution_layer",
    "compose_constitution",
    "render_constitution_template",
    "generate_all_constitutions",
    # Rosters
    "generate_available_agents",
    "generate_available_validators",
    # Rules
    "RulesRegistry",
    "compose_rules",
    "extract_anchor_content",
    "load_bundled_rules",
    "get_rules_for_role_api",
    "filter_rules",
    "FilePatternRegistry",
    "AnchorNotFoundError",
    "RulesCompositionError",
]



