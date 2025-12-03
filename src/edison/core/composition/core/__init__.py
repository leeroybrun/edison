"""Core composition building blocks (discovery, sections, schema, paths)."""
from __future__ import annotations

from .discovery import LayerDiscovery, LayerSource
from .errors import (
    CompositionValidationError,
    CompositionNotFoundError,
    CompositionShadowingError,
    CompositionSectionError,
    AnchorNotFoundError,
    RulesCompositionError,
)
from .paths import (
    CompositionPathResolver,
    ResolvedPaths,
    get_resolved_paths,
)
from .schema import CompositionSchema, ContentTypeSchema
from .sections import (
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
    # Strategies
    "CompositionContext",
    "LayerContent",
    "MarkdownCompositionStrategy",
]
