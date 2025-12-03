"""Core composition engine.

This module contains the layered composition system that handles
section-based and concatenate composition modes.

Public API:
- LayeredComposer: Main composer class
- compose(): Compose single entity
- compose_all(): Compose all entities of a type
- CompositionMode: Enum for composition modes
- ConcatenateComposer: Guideline-style paragraph composition
"""
from __future__ import annotations

from .composer import LayeredComposer
from .discovery import LayerDiscovery, LayerSource
from .errors import (
    CompositionValidationError,
    CompositionNotFoundError,
    CompositionShadowingError,
    CompositionSectionError,
    AnchorNotFoundError,
    RulesCompositionError,
)
from .modes import (
    CompositionMode,
    ConcatenateComposer,
    DEFAULT_MODE,
    get_mode,
    get_composer,
)
from .paths import (
    CompositionPathResolver,
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
from ..strategies import (
    CompositionContext,
    LayerContent,
    MarkdownCompositionStrategy,
)
from .types import ComposeResult

__all__ = [
    # Composer
    "LayeredComposer",
    # Discovery
    "LayerDiscovery",
    "LayerSource",
    # Types
    "ComposeResult",
    # Errors
    "CompositionValidationError",
    "CompositionNotFoundError",
    "CompositionShadowingError",
    "CompositionSectionError",
    "AnchorNotFoundError",
    "RulesCompositionError",
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
    # Strategies
    "CompositionContext",
    "LayerContent",
    "MarkdownCompositionStrategy",
]


