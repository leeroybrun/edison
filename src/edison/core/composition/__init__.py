"""Composition package exposing include resolution and composition engines.

Note: Registry classes are NOT re-exported here to avoid circular imports.
Import them directly from edison.core.composition.registries instead.
"""
from __future__ import annotations

# Core composition engine
from .core import (
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
    # Paths
    CompositionPathResolver,
    ResolvedPaths,
    get_resolved_paths,
    # Schema
    CompositionSchema,
    ContentTypeSchema,
    # Sections
    SectionParser,
    SectionRegistry,
    SectionMode,
    ParsedSection,
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

# IDE composition imports are now lazy (see __getattr__ below) to avoid circular imports


# Lazy imports for registries to avoid circular imports
def __getattr__(name: str):
    """Lazy import registry classes to avoid circular imports."""
    # Registry classes
    registry_imports = {
        "AgentRegistry": ".registries.agents",
        "AgentError": ".registries.agents",
        "AgentNotFoundError": ".registries.agents",
        "compose_agent": ".registries.agents",
        "ValidatorRegistry": ".registries.validators",
        "collect_validators": ".registries.validators",
        "infer_validator_metadata": ".registries.validators",
        "normalize_validator_entries": ".registries.validators",
        "GuidelineRegistry": ".registries.guidelines",
        "GuidelineCompositionResult": ".registries.guidelines",
        "GuidelinePaths": ".registries.guidelines",
        "compose_guideline": ".registries.guidelines",
        "ConstitutionRegistry": ".registries.constitutions",
        "ConstitutionResult": ".registries.constitutions",
        "generate_all_constitutions": ".registries.constitutions",
        "generate_canonical_entry": ".generators.roots",
        "get_rules_for_role": ".registries.rules",
    }

    # IDE composition classes (from adapters.components and adapters.platforms)
    ide_imports = {
        # Commands
        "CommandArg": ("edison.core.adapters.components.commands", True),
        "CommandDefinition": ("edison.core.adapters.components.commands", True),
        "CommandComposer": ("edison.core.adapters.components.commands", True),
        "PlatformAdapter": ("edison.core.adapters", False),
        "ClaudeCommandAdapter": ("edison.core.adapters.components.commands", True),
        "CursorCommandAdapter": ("edison.core.adapters.components.commands", True),
        "CodexCommandAdapter": ("edison.core.adapters.components.commands", True),
        "compose_commands": ("edison.core.adapters.components.commands", True),
        # Hooks
        "HookComposer": ("edison.core.adapters.components.hooks", True),
        "HookDefinition": ("edison.core.adapters.components.hooks", True),
        "compose_hooks": ("edison.core.adapters.components.hooks", True),
        # Settings
        "ALLOWED_TYPES": ("edison.core.adapters.components.settings", True),
        "SettingsComposer": ("edison.core.adapters.components.settings", True),
        "merge_permissions": ("edison.core.adapters.components.settings", True),
    }

    if name in registry_imports:
        import importlib
        module = importlib.import_module(registry_imports[name], package="edison.core.composition")
        return getattr(module, name)

    if name in ide_imports:
        import importlib
        module_path, direct = ide_imports[name]
        module = importlib.import_module(module_path)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core
    "LayerDiscovery",
    "LayerSource",
    "ComposeResult",
    "CompositionValidationError",
    "CompositionNotFoundError",
    "CompositionShadowingError",
    "CompositionSectionError",
    # Modes
    # Paths
    "CompositionPathResolver",
    "ResolvedPaths",
    "get_resolved_paths",
    # Schema
    "CompositionSchema",
    "ContentTypeSchema",
    # Sections
    "SectionParser",
    "SectionRegistry",
    "SectionMode",
    "ParsedSection",
    # Registries - Agents (lazy)
    "AgentRegistry",
    "AgentError",
    "AgentNotFoundError",
    "compose_agent",
    # Registries - Validators (lazy)
    "ValidatorRegistry",
    "collect_validators",
    "infer_validator_metadata",
    "normalize_validator_entries",
    # Registries - Guidelines (lazy)
    "GuidelineRegistry",
    "GuidelineCompositionResult",
    "GuidelinePaths",
    "compose_guideline",
    # Registries - Constitutions (lazy)
    "generate_all_constitutions",
    # Registries - Rosters (lazy)
    "generate_canonical_entry",
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
    # Constitutions
    "ConstitutionRegistry",
    "ConstitutionResult",
    # Rules
    "get_rules_for_role",
    # IDE
    "CommandArg",
    "CommandDefinition",
    "CommandComposer",
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
    "PlatformAdapter",
]
