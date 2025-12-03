"""Template transformers for Edison composition engine.

This module provides the transformation components for the TemplateEngine.
Each transformer handles a specific category of template processing:

- base: Abstract base class and pipeline infrastructure
- conditionals: Condition evaluation and conditional blocks
- includes: File and section inclusion
- loops: Collection iteration ({{#each}})
- variables: Config, context, and path variable substitution
- references: Section references without embedding
"""
from __future__ import annotations

from .base import ContentTransformer, TransformContext, TransformerPipeline
from .conditionals import ConditionEvaluator, ConditionalProcessor, CompositionContext
from .includes import IncludeResolver, SectionExtractor, IncludeTransformer
from .loops import LoopExpander
from .variables import (
    ConfigVariableTransformer,
    ContextVariableTransformer,
    PathVariableTransformer,
    VariableTransformer,
)
from .references import ReferenceRenderer

__all__ = [
    # Base classes
    "ContentTransformer",
    "TransformContext",
    "TransformerPipeline",
    # Conditionals
    "ConditionEvaluator",
    "ConditionalProcessor",
    "CompositionContext",
    # Includes
    "IncludeResolver",
    "SectionExtractor",
    "IncludeTransformer",
    # Loops
    "LoopExpander",
    # Variables
    "ConfigVariableTransformer",
    "ContextVariableTransformer",
    "PathVariableTransformer",
    "VariableTransformer",
    # References
    "ReferenceRenderer",
]
