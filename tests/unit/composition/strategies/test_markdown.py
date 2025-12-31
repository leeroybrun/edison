"""Tests for MarkdownCompositionStrategy.

Tests section-based composition, deduplication, and template processing.
"""
from pathlib import Path

import pytest

from edison.core.composition.strategies.base import (
    CompositionContext,
    LayerContent,
)
from edison.core.composition.strategies.markdown import MarkdownCompositionStrategy


class TestMarkdownCompositionStrategy:
    """Test MarkdownCompositionStrategy class."""

    def test_strategy_initialization(self) -> None:
        """Test strategy can be initialized with config."""
        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
            dedupe_shingle_size=12,
            enable_template_processing=True,
        )

        assert strategy.enable_sections is True
        assert strategy.enable_dedupe is False
        assert strategy.dedupe_shingle_size == 12
        assert strategy.enable_template_processing is True

    def test_compose_empty_layers(self) -> None:
        """Test compose with no layers returns empty string."""
        strategy = MarkdownCompositionStrategy()
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose([], context)

        assert result == ""

    def test_compose_single_layer_no_sections(self) -> None:
        """Test compose with single layer and sections disabled."""
        strategy = MarkdownCompositionStrategy(enable_sections=False)
        layers = [LayerContent(content="# Title\n\nContent", source="core")]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        assert result == "# Title\n\nContent"

    def test_compose_multiple_layers_concatenation(self) -> None:
        """Test simple concatenation when sections disabled."""
        strategy = MarkdownCompositionStrategy(enable_sections=False)
        layers = [
            LayerContent(content="# Core", source="core"),
            LayerContent(content="# Pack", source="pack:python"),
            LayerContent(content="# Project", source="project"),
        ]
        context = CompositionContext(active_packs=["python"], config={})

        result = strategy.compose(layers, context)

        assert result == "# Core\n\n# Pack\n\n# Project"

    def test_compose_sections_basic(self) -> None:
        """Test section-based composition with SECTION markers."""
        strategy = MarkdownCompositionStrategy(enable_sections=True)
        layers = [
            LayerContent(
                content=(
                    "<!-- SECTION: header -->\n"
                    "# Title\n"
                    "<!-- /SECTION: header -->\n"
                    "\n"
                    "<!-- SECTION: body -->\n"
                    "Body content\n"
                    "<!-- /SECTION: body -->"
                ),
                source="core",
            ),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Markers should be stripped
        assert "<!-- SECTION:" not in result
        assert "# Title" in result
        assert "Body content" in result

    def test_compose_sections_with_extend(self) -> None:
        """Test section extension with EXTEND markers."""
        strategy = MarkdownCompositionStrategy(enable_sections=True, enable_template_processing=False)
        layers = [
            LayerContent(
                content=(
                    "<!-- SECTION: content -->\n"
                    "Base content\n"
                    "<!-- /SECTION: content -->"
                ),
                source="core",
            ),
            LayerContent(
                content=(
                    "<!-- EXTEND: content -->\n"
                    "Extended content\n"
                    "<!-- /EXTEND -->"  # Note: No section name in closing tag
                ),
                source="pack:python",
            ),
        ]
        context = CompositionContext(active_packs=["python"], config={})

        result = strategy.compose(layers, context)

        # Both base and extended content should be present
        assert "Base content" in result
        assert "Extended content" in result
        assert "<!-- SECTION:" not in result

    def test_dedupe_disabled_by_default(self) -> None:
        """Test deduplication is disabled by default."""
        strategy = MarkdownCompositionStrategy(enable_dedupe=False)
        layers = [
            LayerContent(
                content="Line 1\nLine 2\nLine 1",  # Duplicate
                source="core",
            ),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Duplicates should remain
        assert result.count("Line 1") == 2

    def test_dedupe_enabled_removes_duplicates(self) -> None:
        """Test deduplication removes duplicate paragraphs."""
        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=True,
            dedupe_shingle_size=3,
            enable_template_processing=False,
        )
        layers = [
            LayerContent(
                content=(
                    "This is the first paragraph with enough words for shingling.\n\n"
                    "This is a second paragraph with different content.\n\n"
                    "This is the first paragraph with enough words for shingling."
                ),
                source="core",
            ),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # First paragraph should appear only once (later occurrence kept)
        assert result.count("This is the first paragraph with enough words for shingling") == 1
        assert "This is a second paragraph with different content" in result

    def test_dedupe_does_not_break_fenced_code_blocks(self) -> None:
        """Deduplication must not remove parts of fenced code blocks.

        The paragraph splitter is blank-line based. If it were to split *inside*
        a fenced code block, dedupe could remove the paragraph containing the
        closing fence delimiter, producing an unbalanced fence that then breaks
        downstream template processing.
        """
        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=True,
            dedupe_shingle_size=3,
            enable_template_processing=False,
        )
        dup = "dup dup dup dup dup dup dup"
        content = "\n".join(
            [
                "```txt",
                "x",
                "",
                dup,
                "```",
                "",
                dup,
                "",
            ]
        )
        layers = [LayerContent(content=content, source="core")]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Fence must remain balanced.
        assert result.count("```") == 2
        # Both dup lines must remain: one inside the code fence, one outside.
        assert result.count(dup) == 2

    def test_template_processing_disabled(self) -> None:
        """Test template processing can be disabled."""
        strategy = MarkdownCompositionStrategy(enable_template_processing=False)
        layers = [
            LayerContent(content="{{variable}}", source="core"),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Template variable should remain unprocessed
        assert result == "{{variable}}"

    def test_layer_properties(self) -> None:
        """Test LayerContent properties are correctly identified."""
        core_layer = LayerContent(content="core", source="core")
        pack_layer = LayerContent(content="pack", source="pack:python")
        project_layer = LayerContent(content="project", source="project")

        assert core_layer.is_core is True
        assert core_layer.is_pack is False
        assert core_layer.pack_name is None

        assert pack_layer.is_core is False
        assert pack_layer.is_pack is True
        assert pack_layer.pack_name == "python"

        assert project_layer.is_project is True
        assert project_layer.is_core is False


class TestMarkdownCompositionEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content_layers(self) -> None:
        """Test handling of empty content in layers."""
        strategy = MarkdownCompositionStrategy(enable_sections=False)
        layers = [
            LayerContent(content="", source="core"),
            LayerContent(content="# Title", source="pack:python"),
            LayerContent(content="", source="project"),
        ]
        context = CompositionContext(active_packs=["python"], config={})

        result = strategy.compose(layers, context)

        assert result == "# Title"

    def test_whitespace_only_layers(self) -> None:
        """Test handling of whitespace-only content."""
        strategy = MarkdownCompositionStrategy(enable_sections=False)
        layers = [
            LayerContent(content="   \n\n  ", source="core"),
            LayerContent(content="# Title", source="pack:python"),
        ]
        context = CompositionContext(active_packs=["python"], config={})

        result = strategy.compose(layers, context)

        assert result == "# Title"
