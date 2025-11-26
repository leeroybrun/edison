"""Core composition engine.

This module contains the layered composition system that handles
section-based and concatenate composition modes.

Public API:
- LayeredComposer: Main composer class
- compose(): Compose single entity
- compose_all(): Compose all entities of a type
- CompositionMode: Enum for composition modes
"""
from __future__ import annotations

from .composer import LayeredComposer
from .discovery import LayerDiscovery, LayerSource
from .errors import (
    CompositionValidationError,
    CompositionNotFoundError,
    CompositionShadowingError,
    CompositionSectionError,
)
from .paths import (
    CompositionPathResolver,
    UnifiedPathResolver,  # Backward compatibility alias
    ResolvedPaths,
    get_resolved_paths,
)
from .schema import CompositionSchema, ContentTypeSchema
from .sections import (
    SectionComposer,
    SectionParser,
    SectionRegistry,
    SectionMode,
    ParsedSection,
)

__all__ = [
    # Composer
    "LayeredComposer",
    # Discovery
    "LayerDiscovery",
    "LayerSource",
    # Errors
    "CompositionValidationError",
    "CompositionNotFoundError",
    "CompositionShadowingError",
    "CompositionSectionError",
    # Paths
    "CompositionPathResolver",
    "UnifiedPathResolver",
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
]
