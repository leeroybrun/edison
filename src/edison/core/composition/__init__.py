"""Composition package exposing include resolution and composition engines."""
from __future__ import annotations

# Core composition engine
from .core import (
    # Composer
    LayeredComposer,
    # Discovery
    LayerDiscovery,
    LayerSource,
    # Types
    ComposeResult,
    # Errors
    CompositionValidationError,
    CompositionNotFoundError,
    CompositionShadowingError,
    CompositionSectionError,
    # Modes
    CompositionMode,
    ConcatenateComposer,
    DEFAULT_MODE,
    get_mode,
    get_composer,
    # Paths
    CompositionPathResolver,
    ResolvedPaths,
    get_resolved_paths,
    # Schema
    CompositionSchema,
    ContentTypeSchema,
    # Sections
    SectionComposer,
    SectionParser,
    SectionRegistry,
    SectionMode,
    ParsedSection,
)

# Registries
from .registries import (
    # Agents
    AgentRegistry,
    AgentError,
    AgentNotFoundError,
    AgentTemplateError,
    CoreAgent,
    PackOverlay,
    compose_agent,
    # Validators
    ValidatorRegistry,
    collect_validators,
    infer_validator_metadata,
    normalize_validator_entries,
    # Guidelines
    GuidelineRegistry,
    GuidelineCompositionResult,
    GuidelinePaths,
    compose_guideline,
    # Constitutions
    get_rules_for_role,
    load_constitution_layer,
    compose_constitution,
    render_constitution_template,
    generate_all_constitutions,
    # Rosters
    generate_available_agents,
    generate_available_validators,
)

# Output handling
from .output import (
    # Config
    OutputConfig,
    ClientOutputConfig,
    SyncConfig,
    OutputConfigLoader,
    get_output_config,
    # Headers
    build_generated_header,
    load_header_template,
    resolve_version,
    # Formatting
    format_for_zen,
    format_rules_context,
    compose_for_role,
    # Document generation
    generate_state_machine_doc,
)

# Includes
from .includes import (
    ComposeError,
    resolve_includes,
    get_cache_dir,
    validate_composition,
    MAX_DEPTH,
    _repo_root,
)

# Packs
from .packs import auto_activate_packs

# Audit
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

# IDE composition
from .ide import (
    CommandArg,
    CommandDefinition,
    CommandComposer,
    PlatformAdapter,
    ClaudeCommandAdapter,
    CursorCommandAdapter,
    CodexCommandAdapter,
    compose_commands,
    HookComposer,
    HookDefinition,
    compose_hooks,
    ALLOWED_TYPES,
    SettingsComposer,
    merge_permissions,
)

__all__ = [
    # Core
    "LayeredComposer",
    "LayerDiscovery",
    "LayerSource",
    "ComposeResult",
    "CompositionValidationError",
    "CompositionNotFoundError",
    "CompositionShadowingError",
    "CompositionSectionError",
    # Modes
    "CompositionMode",
    "ConcatenateComposer",
    "DEFAULT_MODE",
    "get_mode",
    "get_composer",
    # Paths
    "CompositionPathResolver",
    "ResolvedPaths",
    "get_resolved_paths",
    # Schema
    "CompositionSchema",
    "ContentTypeSchema",
    # Sections
    "SectionComposer",
    "SectionParser",
    "SectionRegistry",
    "SectionMode",
    "ParsedSection",
    # Registries - Agents
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "AgentTemplateError",
    "CoreAgent",
    "PackOverlay",
    "compose_agent",
    # Registries - Validators
    "ValidatorRegistry",
    "collect_validators",
    "infer_validator_metadata",
    "normalize_validator_entries",
    # Registries - Guidelines
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    # Registries - Constitutions
    "get_rules_for_role",
    "load_constitution_layer",
    "compose_constitution",
    "render_constitution_template",
    "generate_all_constitutions",
    # Registries - Rosters
    "generate_available_agents",
    "generate_available_validators",
    # Output
    "OutputConfig",
    "ClientOutputConfig",
    "SyncConfig",
    "OutputConfigLoader",
    "get_output_config",
    "build_generated_header",
    "load_header_template",
    "resolve_version",
    "format_for_zen",
    "format_rules_context",
    "compose_for_role",
    "generate_state_machine_doc",
    # Includes
    "ComposeError",
    "resolve_includes",
    "get_cache_dir",
    "validate_composition",
    "MAX_DEPTH",
    "_repo_root",
    # Packs
    "auto_activate_packs",
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
    # IDE
    "CommandArg",
    "CommandDefinition",
    "CommandComposer",
    "PlatformAdapter",
    "ClaudeCommandAdapter",
    "CursorCommandAdapter",
    "CodexCommandAdapter",
    "compose_commands",
    "HookComposer",
    "HookDefinition",
    "compose_hooks",
    "ALLOWED_TYPES",
    "SettingsComposer",
    "merge_permissions",
]
