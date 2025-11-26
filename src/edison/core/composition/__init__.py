"""Composition package exposing include resolution and composition engines."""

from .includes import (
    ComposeError,
    resolve_includes,
    get_cache_dir,
    validate_composition,
    MAX_DEPTH,
    _repo_root,
)
from .composers import (
    ComposeResult,
    compose_prompt,
    compose_guidelines,
    CompositionEngine,
)
from .constitution import (
    get_rules_for_role,
    load_constitution_layer,
    compose_constitution,
    render_constitution_template,
    generate_all_constitutions,
)
from .packs import auto_activate_packs
from .rosters import generate_available_agents, generate_available_validators
from .state_machine import generate_state_machine_doc
from ..utils.text import (
    dry_duplicate_report,
    render_conditional_includes,
    ENGINE_VERSION,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)
from .guidelines import (
    GuidelineRegistry,
    GuidelineCompositionResult,
    GuidelinePaths,
    compose_guideline,
)
from .agents import (
    AgentRegistry,
    AgentError,
    AgentNotFoundError,
    AgentTemplateError,
    CoreAgent,
    PackOverlay,
    compose_agent,
)
from .audit import (
    GuidelineRecord,
    GuidelineCategory,
    discover_guidelines,
    build_shingle_index,
    duplication_matrix,
    purity_violations,
    project_terms,
    DEFAULT_PROJECT_TERMS,
    PACK_TECH_TERMS,
)

__all__ = [
    "ComposeError",
    "ComposeResult",
    "compose_prompt",
    "compose_guidelines",
    "resolve_includes",
    "render_conditional_includes",
    "auto_activate_packs",
    "validate_composition",
    "dry_duplicate_report",
    "ENGINE_VERSION",
    "MAX_DEPTH",
    "get_cache_dir",
    "CompositionEngine",
    "_repo_root",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    # Guidelines
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    # Agents
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "AgentTemplateError",
    "CoreAgent",
    "PackOverlay",
    "compose_agent",
    # Audit
    "GuidelineRecord",
    "GuidelineCategory",
    "discover_guidelines",
    "build_shingle_index",
    "duplication_matrix",
    "purity_violations",
    "project_terms",
    "DEFAULT_PROJECT_TERMS",
    "PACK_TECH_TERMS",
    # Constitutions
    "get_rules_for_role",
    "load_constitution_layer",
    "compose_constitution",
    "render_constitution_template",
    "generate_all_constitutions",
    # Rosters
    "generate_available_agents",
    "generate_available_validators",
    "generate_state_machine_doc",
]
