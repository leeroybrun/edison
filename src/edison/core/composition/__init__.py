"""Composition package exposing include resolution and composition engines.

Note: AgentRegistry and ValidatorRegistry for metadata lookup are now in core.registries.
Use: from edison.core.registries import AgentRegistry, ValidatorRegistry

Note: Output configuration is now handled by CompositionConfig in
edison.core.config.domains.composition.
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
    # Sections
    SectionParser,
    SectionRegistry,
    SectionMode,
    ParsedSection,
)

# Output handling (headers and formatting only - config is in CompositionConfig)
from .output import (
    # Headers
    build_generated_header,
    load_header_template,
    resolve_version,
    # Formatting
    format_for_zen,
    format_rules_context,
    compose_for_role,
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
    # Registry classes that still exist
    registry_imports = {
        "ConstitutionRegistry": ".registries.constitutions",
        "generate_all_constitutions": ".registries.constitutions",
    }
    
    # Redirects to new core.registries location
    core_registry_redirects = {
        "AgentRegistry": ("edison.core.registries.agents", "AgentRegistry"),
        "ValidatorRegistry": ("edison.core.registries.validators", "ValidatorRegistry"),
    }
    
    # Rules are now in core.rules
    rules_imports = {
        "get_rules_for_role": ("edison.core.rules.registry", "get_rules_for_role"),
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
        "ALLOWED_TYPES": ("edison.core.adapters.components.hooks", True),
        "SettingsComposer": ("edison.core.adapters.components.settings", True),
    }

    if name in registry_imports:
        import importlib
        module = importlib.import_module(registry_imports[name], package="edison.core.composition")
        return getattr(module, name)
    
    if name in core_registry_redirects:
        import importlib
        module_path, attr_name = core_registry_redirects[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    
    if name in rules_imports:
        import importlib
        module_path, attr_name = rules_imports[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)

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
    # Paths
    "CompositionPathResolver",
    "ResolvedPaths",
    "get_resolved_paths",
    # Sections
    "SectionParser",
    "SectionRegistry",
    "SectionMode",
    "ParsedSection",
    # Registries - redirected to core.registries (lazy)
    "AgentRegistry",
    "ValidatorRegistry",
    # Registries - Constitutions (lazy)
    "ConstitutionRegistry",
    "generate_all_constitutions",
    # Output (headers and formatting)
    "build_generated_header",
    "load_header_template",
    "resolve_version",
    "format_for_zen",
    "format_rules_context",
    "compose_for_role",
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
    "PlatformAdapter",
]
