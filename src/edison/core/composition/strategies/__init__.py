"""Composition strategies module.

This module provides composition strategies for transforming layered content:
- base: Base classes (CompositionStrategy, LayerContent, CompositionContext)
- markdown: Markdown composition with sections, deduplication, and templates
"""
from .base import CompositionContext, CompositionStrategy, LayerContent
from .markdown import MarkdownCompositionStrategy

__all__ = [
    "CompositionContext",
    "CompositionStrategy",
    "LayerContent",
    "MarkdownCompositionStrategy",
]
