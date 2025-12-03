"""Tests for MarkdownCompositionStrategy.

TDD: These tests are written FIRST before implementation.

MarkdownCompositionStrategy is THE unified strategy for ALL markdown content:
- Section-based composition (SECTION/EXTEND markers)
- DRY deduplication (shingle-based, optional)
- Include resolution
- Template processing via TemplateEngine
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest


@dataclass
class LayerContent:
    """Content from a composition layer."""

    content: str
    source: str  # "core" | "pack:{name}" | "project"
    path: Optional[Path] = None


class TestMarkdownCompositionStrategyBasic:
    """Basic tests for MarkdownCompositionStrategy."""

    def test_strategy_instantiation(self) -> None:
        """Strategy can be instantiated with default config."""
        from edison.core.composition.strategies import MarkdownCompositionStrategy

        strategy = MarkdownCompositionStrategy()

        assert strategy.enable_sections is True
        assert strategy.enable_dedupe is False
        assert strategy.dedupe_shingle_size == 12
        assert strategy.enable_template_processing is True

    def test_strategy_instantiation_with_config(self) -> None:
        """Strategy can be instantiated with custom config."""
        from edison.core.composition.strategies import MarkdownCompositionStrategy

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=True,
            dedupe_shingle_size=8,
            enable_template_processing=False,
        )

        assert strategy.enable_sections is False
        assert strategy.enable_dedupe is True
        assert strategy.dedupe_shingle_size == 8
        assert strategy.enable_template_processing is False

    def test_compose_single_layer_passthrough(self) -> None:
        """Single layer content passes through unchanged."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(content="# Hello\n\nWorld", source="core"),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        assert result.strip() == "# Hello\n\nWorld"


class TestMarkdownCompositionStrategySections:
    """Tests for section-based composition."""

    def test_compose_with_section_markers(self) -> None:
        """Content with SECTION markers is processed correctly."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(
                content="""# Agent
<!-- SECTION: intro -->
Core intro content.
<!-- /SECTION: intro -->
""",
                source="core",
            ),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Section markers should be stripped in final output
        assert "Core intro content." in result
        assert "<!-- SECTION:" not in result

    def test_compose_with_extend_markers(self) -> None:
        """EXTEND markers add content to existing sections."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(
                content="""# Agent
<!-- SECTION: intro -->
Core intro.
<!-- /SECTION: intro -->
""",
                source="core",
            ),
            LayerContent(
                content="""<!-- EXTEND: intro -->
Pack extension.
<!-- /EXTEND -->
""",
                source="pack:react",
            ),
        ]
        context = CompositionContext(active_packs=["react"], config={})

        result = strategy.compose(layers, context)

        # Both core and extension content should be present
        assert "Core intro." in result
        assert "Pack extension." in result

    def test_compose_multiple_layers(self) -> None:
        """Content from all layers is composed in order."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(
                content="""# Agent
<!-- SECTION: rules -->
Core rules.
<!-- /SECTION: rules -->
""",
                source="core",
            ),
            LayerContent(
                content="""<!-- EXTEND: rules -->
Pack rules.
<!-- /EXTEND -->
""",
                source="pack:python",
            ),
            LayerContent(
                content="""<!-- EXTEND: rules -->
Project rules.
<!-- /EXTEND -->
""",
                source="project",
            ),
        ]
        context = CompositionContext(active_packs=["python"], config={})

        result = strategy.compose(layers, context)

        # All content should be present
        assert "Core rules." in result
        assert "Pack rules." in result
        assert "Project rules." in result


class TestMarkdownCompositionStrategyDedupe:
    """Tests for DRY deduplication feature."""

    def test_dedupe_removes_duplicate_paragraphs(self) -> None:
        """Duplicate paragraphs are removed based on shingles."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=True,
            dedupe_shingle_size=6,  # Smaller for test
            enable_template_processing=False,
        )

        # Create duplicate content across layers
        duplicate_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

        layers = [
            LayerContent(
                content=f"# Core\n\n{duplicate_text}\n",
                source="core",
            ),
            LayerContent(
                content=f"# Pack\n\n{duplicate_text}\n\nUnique pack content.\n",
                source="pack:test",
            ),
        ]
        context = CompositionContext(active_packs=["test"], config={})

        result = strategy.compose(layers, context)

        # Duplicate should appear only once (from project layer - highest priority)
        count = result.count(duplicate_text)
        assert count == 1, f"Expected 1 occurrence, found {count}"
        assert "Unique pack content." in result

    def test_dedupe_disabled_by_default(self) -> None:
        """Deduplication is disabled by default."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_template_processing=False,
        )

        duplicate_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

        layers = [
            LayerContent(content=f"# Core\n\n{duplicate_text}\n", source="core"),
            LayerContent(content=f"# Pack\n\n{duplicate_text}\n", source="pack:test"),
        ]
        context = CompositionContext(active_packs=["test"], config={})

        result = strategy.compose(layers, context)

        # Without dedupe, both should be present
        count = result.count(duplicate_text)
        assert count == 2, f"Expected 2 occurrences without dedupe, found {count}"

    def test_dedupe_respects_layer_priority(self) -> None:
        """Deduplication keeps content from higher priority layers."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=True,
            dedupe_shingle_size=6,
            enable_template_processing=False,
        )

        duplicate_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

        layers = [
            LayerContent(
                content=f"# Core Header\n\n{duplicate_text}\n\nCore unique.",
                source="core",
            ),
            LayerContent(
                content=f"# Project Header\n\n{duplicate_text}\n\nProject unique.",
                source="project",
            ),
        ]
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose(layers, context)

        # Project content has priority, should keep project's duplicate
        assert "Project unique." in result
        # Core duplicate should be removed
        assert result.count(duplicate_text) == 1


class TestMarkdownCompositionStrategyTemplateProcessing:
    """Tests for template variable processing."""

    def test_template_variables_resolved(self) -> None:
        """Template variables are resolved when enabled."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=False,
            enable_template_processing=True,
        )

        layers = [
            LayerContent(
                content="# Agent\n\nProject: {{config.project.name}}\n",
                source="core",
            ),
        ]
        context = CompositionContext(
            active_packs=[],
            config={"project": {"name": "TestProject"}},
        )

        result = strategy.compose(layers, context)

        assert "TestProject" in result
        assert "{{config.project.name}}" not in result

    def test_template_processing_disabled(self) -> None:
        """Template variables are left unresolved when disabled."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(
                content="# Agent\n\nProject: {{config.project.name}}\n",
                source="core",
            ),
        ]
        context = CompositionContext(
            active_packs=[],
            config={"project": {"name": "TestProject"}},
        )

        result = strategy.compose(layers, context)

        # Variable should remain unresolved
        assert "{{config.project.name}}" in result


class TestCompositionContext:
    """Tests for CompositionContext dataclass."""

    def test_context_creation(self) -> None:
        """CompositionContext can be created with required fields."""
        from edison.core.composition.strategies import CompositionContext

        context = CompositionContext(
            active_packs=["react", "nextjs"],
            config={"key": "value"},
        )

        assert context.active_packs == ["react", "nextjs"]
        assert context.config == {"key": "value"}

    def test_context_optional_fields(self) -> None:
        """CompositionContext handles optional fields."""
        from edison.core.composition.strategies import CompositionContext

        context = CompositionContext(
            active_packs=[],
            config={},
            project_root=Path("/tmp/test"),
            source_dir=Path("/tmp/test/src"),
        )

        assert context.project_root == Path("/tmp/test")
        assert context.source_dir == Path("/tmp/test/src")


class TestLayerContent:
    """Tests for LayerContent dataclass."""

    def test_layer_content_creation(self) -> None:
        """LayerContent can be created with required fields."""
        from edison.core.composition.strategies import LayerContent

        layer = LayerContent(content="# Hello", source="core")

        assert layer.content == "# Hello"
        assert layer.source == "core"
        assert layer.path is None

    def test_layer_content_with_path(self) -> None:
        """LayerContent can include optional path."""
        from edison.core.composition.strategies import LayerContent

        layer = LayerContent(
            content="# Hello",
            source="pack:react",
            path=Path("/tmp/agents/builder.md"),
        )

        assert layer.path == Path("/tmp/agents/builder.md")


class TestMarkdownCompositionStrategyIntegration:
    """Integration tests combining multiple features."""

    def test_full_pipeline_sections_and_dedupe(self) -> None:
        """Full pipeline with sections AND dedupe enabled."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=True,
            enable_dedupe=True,
            dedupe_shingle_size=6,
            enable_template_processing=False,
        )

        duplicate_text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"

        layers = [
            LayerContent(
                content=f"""# Agent
<!-- SECTION: intro -->
{duplicate_text}
<!-- /SECTION: intro -->
""",
                source="core",
            ),
            LayerContent(
                content=f"""<!-- EXTEND: intro -->
{duplicate_text}
Unique extension.
<!-- /EXTEND -->
""",
                source="pack:test",
            ),
        ]
        context = CompositionContext(active_packs=["test"], config={})

        result = strategy.compose(layers, context)

        # Sections should be composed
        assert "Unique extension." in result
        # Duplicate should be deduped
        assert result.count(duplicate_text) == 1
        # Section markers should be stripped
        assert "<!-- SECTION:" not in result

    def test_empty_layers_handled(self) -> None:
        """Empty layer list returns empty string."""
        from edison.core.composition.strategies import (
            CompositionContext,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy()
        context = CompositionContext(active_packs=[], config={})

        result = strategy.compose([], context)

        assert result == ""

    def test_layer_order_preserved(self) -> None:
        """Layers are processed in order: core → packs → project."""
        from edison.core.composition.strategies import (
            CompositionContext,
            LayerContent,
            MarkdownCompositionStrategy,
        )

        strategy = MarkdownCompositionStrategy(
            enable_sections=False,
            enable_dedupe=False,
            enable_template_processing=False,
        )

        layers = [
            LayerContent(content="CORE", source="core"),
            LayerContent(content="PACK1", source="pack:alpha"),
            LayerContent(content="PACK2", source="pack:beta"),
            LayerContent(content="PROJECT", source="project"),
        ]
        context = CompositionContext(active_packs=["alpha", "beta"], config={})

        result = strategy.compose(layers, context)

        # All content should be concatenated in order
        core_pos = result.find("CORE")
        pack1_pos = result.find("PACK1")
        pack2_pos = result.find("PACK2")
        project_pos = result.find("PROJECT")

        assert core_pos < pack1_pos < pack2_pos < project_pos
