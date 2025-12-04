"""Base class for content transformers in the TemplateEngine.

The TemplateEngine uses a pipeline of transformers to process templates.
Each transformer handles a specific category of template processing.

Transformation Order (9 steps):
1. INCLUDES        - {{include:path}}, {{include-optional:path}}
2. SECTION EXTRACT - {{include-section:path#name}}
3. CONDITIONALS    - {{include-if:COND:path}}, {{if:COND}}...{{/if}}
4. LOOPS           - {{#each collection}}...{{/each}}
5. CONFIG VARS     - {{config.path.to.value}}
6. CONTEXT VARS    - {{source_layers}}, {{timestamp}}
7. PATH VARS       - {{PROJECT_EDISON_DIR}}
8. REFERENCES      - {{reference-section:path#name|purpose}}
9. VALIDATION      - Check for unresolved {{...}}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from edison.core.config import ConfigManager


@dataclass
class TransformContext:
    """Context provided to transformers during processing.

    Contains all information needed for template transformation:
    - Configuration values
    - Active packs list
    - Project paths
    - Runtime context variables
    - Tracking for reporting
    """

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    active_packs: List[str] = field(default_factory=list)

    # Paths
    project_root: Optional[Path] = None
    source_dir: Optional[Path] = None  # Directory to resolve includes from

    # Runtime context variables (str for simple substitution, list/dict for loops)
    context_vars: Dict[str, Any] = field(default_factory=dict)

    # Tracking for reports
    includes_resolved: Set[str] = field(default_factory=set)
    sections_extracted: Set[str] = field(default_factory=set)
    variables_substituted: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    conditionals_evaluated: int = 0

    def get_config(self, path: str) -> Any:
        """Get config value by dot-separated path.

        Args:
            path: Dot-separated path like 'features.auth.enabled'

        Returns:
            The config value or None if not found
        """
        parts = path.split(".")
        current: Any = self.config
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current

    def record_include(self, path: str) -> None:
        """Record that an include was resolved."""
        self.includes_resolved.add(path)

    def record_section_extract(self, path: str, section: str) -> None:
        """Record that a section was extracted."""
        self.sections_extracted.add(f"{path}#{section}")

    def record_variable(self, name: str, resolved: bool) -> None:
        """Record variable resolution result."""
        if resolved:
            self.variables_substituted.add(name)
        else:
            self.variables_missing.add(name)

    def record_conditional(self) -> None:
        """Record that a conditional was evaluated."""
        self.conditionals_evaluated += 1


class ContentTransformer(ABC):
    """Abstract base class for content transformers.

    Each transformer handles a specific type of template directive.
    Transformers are stateless and receive context through the transform() method.

    Example:
        class IncludeTransformer(ContentTransformer):
            def transform(self, content: str, context: TransformContext) -> str:
                # Process {{include:path}} directives
                return processed_content
    """

    @abstractmethod
    def transform(self, content: str, context: TransformContext) -> str:
        """Transform content using this transformer's rules.

        Args:
            content: Input content to transform
            context: TransformContext with config, paths, and tracking

        Returns:
            Transformed content
        """
        ...

    def get_name(self) -> str:
        """Get transformer name for logging/debugging."""
        return self.__class__.__name__


class TransformerPipeline:
    """Execute a sequence of transformers on content.

    Provides ordered execution with error handling and reporting.

    Example:
        pipeline = TransformerPipeline([
            IncludeTransformer(),
            ConditionalTransformer(),
            VariableTransformer(),
        ])
        result = pipeline.execute(content, context)
    """

    def __init__(self, transformers: List[ContentTransformer]) -> None:
        """Initialize with ordered list of transformers.

        Args:
            transformers: List of transformers to execute in order
        """
        self.transformers = transformers

    def execute(self, content: str, context: TransformContext) -> str:
        """Execute all transformers in sequence.

        Args:
            content: Input content
            context: TransformContext for the pipeline

        Returns:
            Fully transformed content
        """
        result = content
        for transformer in self.transformers:
            result = transformer.transform(result, context)
        return result

    def add_transformer(self, transformer: ContentTransformer) -> None:
        """Add a transformer to the end of the pipeline."""
        self.transformers.append(transformer)

    def insert_transformer(self, index: int, transformer: ContentTransformer) -> None:
        """Insert a transformer at a specific position."""
        self.transformers.insert(index, transformer)
