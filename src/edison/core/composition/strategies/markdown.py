"""Markdown composition strategy for unified content composition.

MarkdownCompositionStrategy is THE unified strategy for ALL markdown content:
- Section-based composition (SECTION/EXTEND markers)
- DRY deduplication (shingle-based, optional)
- Include resolution
- Template processing via TemplateEngine

All markdown registries (agents, validators, guidelines, constitutions, documents)
use this single strategy with different configurations.
"""
from __future__ import annotations

import re
from typing import List, Set, Tuple

from ..core.sections import SectionMode, SectionParser, SectionRegistry
from .base import CompositionContext, CompositionStrategy, LayerContent
from edison.core.utils.profiling import span


class MarkdownCompositionStrategy(CompositionStrategy):
    """THE unified strategy for ALL markdown content.

    Features (all configurable):
    - Section-based composition (SECTION/EXTEND markers)
    - DRY deduplication (shingle-based)
    - Include resolution
    - Template processing via TemplateEngine

    Usage:
        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=True,
            dedupe_shingle_size=12,
            enable_template_processing=True,
        )
        result = strategy.compose(layers, context)
    """

    def __init__(
        self,
        enable_sections: bool = True,
        enable_dedupe: bool = False,
        dedupe_shingle_size: int = 12,
        enable_template_processing: bool = True,
    ) -> None:
        """Initialize the strategy.

        Args:
            enable_sections: Enable section-based composition (SECTION/EXTEND)
            enable_dedupe: Enable DRY deduplication
            dedupe_shingle_size: Shingle size for deduplication (k-word windows)
            enable_template_processing: Enable template variable resolution
        """
        self.parser = SectionParser()
        self.enable_sections = enable_sections
        self.enable_dedupe = enable_dedupe
        self.dedupe_shingle_size = dedupe_shingle_size
        self.enable_template_processing = enable_template_processing

    def compose(
        self,
        layers: List[LayerContent],
        context: CompositionContext,
    ) -> str:
        """Unified composition pipeline.

        Pipeline steps:
        1. Parse sections from each layer (if enabled)
        2. Build section registry (SECTION + EXTEND)
        3. Merge sections into template
        4. Apply DRY deduplication (if enabled) - AFTER composition
        5. Process through TemplateEngine (if enabled)

        Args:
            layers: List of layer content in order (core → packs → project)
            context: Composition context with packs and config

        Returns:
            Composed markdown content
        """
        with span("markdown.compose", layers=len(layers), sections=self.enable_sections, dedupe=self.enable_dedupe):
            if not layers:
                return ""

            # Step 1-3: Section-based composition or concatenation
            if self.enable_sections:
                with span("markdown.compose.sections"):
                    result = self._compose_sections(layers, context)
            else:
                with span("markdown.compose.concat"):
                    result = self._concatenate_layers(layers)

            # Step 4: DRY deduplication AFTER composition
            if self.enable_dedupe:
                with span("markdown.compose.dedupe"):
                    result = self._dedupe_result(result)

            # Step 5: Template processing
            if self.enable_template_processing:
                with span("markdown.compose.templates"):
                    result = self._process_templates(result, context)

            return result

    def _compose_sections(
        self,
        layers: List[LayerContent],
        context: CompositionContext,
    ) -> str:
        """Compose content using section-based approach.

        Args:
            layers: List of layer content
            context: Composition context

        Returns:
            Composed content with sections merged
        """
        if not layers:
            return ""

        # First layer is the template
        template_layer = layers[0]
        template = template_layer.content

        # Initialize section registry
        registry = SectionRegistry()

        # Parse sections from template
        sections = self.parser.parse(template, template_layer.source)
        for section in sections:
            if section.mode == SectionMode.SECTION:
                registry.add_section(section.name, section.content)

        # Process overlay layers
        for layer in layers[1:]:
            overlay_sections = self.parser.parse(layer.content, layer.source)
            for section in overlay_sections:
                if section.mode == SectionMode.EXTEND:
                    registry.add_extension(section.name, section.content)
                elif section.mode == SectionMode.SECTION:
                    # New section defined in overlay
                    registry.add_section(section.name, section.content)

        # Compose final output
        result = self._apply_sections(template, registry)

        # Strip markers
        result = self.parser.strip_markers(result)

        return result

    def _apply_sections(self, template: str, registry: SectionRegistry) -> str:
        """Apply section registry to template.

        Args:
            template: Template content with section markers
            registry: Section registry with sections and extensions

        Returns:
            Template with sections replaced
        """
        result = template

        # Replace section markers with composed content
        for name in registry.sections:
            content = registry.get_section_content(name)
            pattern = re.compile(
                rf"<!--\s*section:\s*{re.escape(name)}\s*-->(.*?)<!--\s*/section:\s*{re.escape(name)}\s*-->",
                re.DOTALL | re.IGNORECASE,
            )
            result = pattern.sub(content, result)

        # Clean up excessive blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    def _concatenate_layers(self, layers: List[LayerContent]) -> str:
        """Simple concatenation of layers.

        Args:
            layers: List of layer content

        Returns:
            Concatenated content
        """
        parts = [layer.content.strip() for layer in layers if layer.content.strip()]
        return "\n\n".join(parts)

    def _dedupe_result(self, content: str) -> str:
        """Apply DRY deduplication to composed result.

        Removes duplicate lines/paragraphs based on shingle matching.
        Later occurrences are kept (they have higher priority),
        earlier occurrences are removed.

        Args:
            content: Composed content to dedupe

        Returns:
            Deduplicated content
        """
        from edison.core.utils.text import _paragraph_shingles, _split_paragraphs

        # Split by double newlines to get paragraphs
        paragraphs = _split_paragraphs(content)

        # If paragraphs don't split well (single-newline separated content),
        # fall back to line-based deduplication
        if len(paragraphs) == 1 and "\n" in paragraphs[0]:
            return self._dedupe_lines(content)

        seen: Set[Tuple[str, ...]] = set()
        keep: List[bool] = []

        # Process paragraphs in reverse order (later = higher priority)
        for idx in range(len(paragraphs) - 1, -1, -1):
            para = paragraphs[idx]
            shingles = _paragraph_shingles(para, k=self.dedupe_shingle_size)
            if shingles and shingles & seen:
                keep.insert(0, False)
            else:
                keep.insert(0, True)
                if shingles:
                    seen |= shingles

        # Rebuild content
        result_paragraphs = [p for p, k in zip(paragraphs, keep) if k]
        return "\n\n".join(result_paragraphs).strip()

    def _dedupe_lines(self, content: str) -> str:
        """Line-based deduplication for single-newline separated content.

        Args:
            content: Content with lines to dedupe

        Returns:
            Deduplicated content
        """
        from edison.core.utils.text import _paragraph_shingles

        lines = content.split("\n")
        seen: Set[Tuple[str, ...]] = set()
        keep: List[bool] = []

        # Process lines in reverse (later = higher priority)
        for idx in range(len(lines) - 1, -1, -1):
            line = lines[idx].strip()
            if not line:
                keep.insert(0, True)  # Keep empty lines
                continue

            shingles = _paragraph_shingles(line, k=self.dedupe_shingle_size)
            if shingles and shingles & seen:
                keep.insert(0, False)
            else:
                keep.insert(0, True)
                if shingles:
                    seen |= shingles

        # Rebuild content
        result_lines = [l for l, k in zip(lines, keep) if k]
        return "\n".join(result_lines).strip()

    def _process_templates(
        self,
        content: str,
        context: CompositionContext,
    ) -> str:
        """Process template variables.

        Args:
            content: Content with template variables
            context: Composition context with config and context_vars

        Returns:
            Content with variables resolved
        """
        from ..engine import TemplateEngine

        engine = TemplateEngine(
            config=context.config,
            packs=context.active_packs,
            project_root=context.project_root,
            source_dir=context.source_dir,
            include_provider=context.include_provider,
            strip_section_markers=context.strip_section_markers,
        )

        # Pass context_vars from CompositionContext to TemplateEngine
        result, _report = engine.process(
            content,
            context_vars=context.context_vars,
        )
        return result


__all__ = [
    "MarkdownCompositionStrategy",
]
