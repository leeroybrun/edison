"""Tests for composition strategies base classes.

Tests for LayerContent, CompositionContext, and CompositionStrategy ABC.
"""
from pathlib import Path

import pytest

from edison.core.composition.strategies.base import (
    CompositionContext,
    CompositionStrategy,
    LayerContent,
)


class TestLayerContent:
    """Test LayerContent dataclass properties."""

    def test_layer_content_core(self) -> None:
        """Test core layer content properties."""
        layer = LayerContent(content="# Core", source="core", path=Path("/core/file.md"))

        assert layer.content == "# Core"
        assert layer.source == "core"
        assert layer.path == Path("/core/file.md")
        assert layer.is_core is True
        assert layer.is_pack is False
        assert layer.is_project is False
        assert layer.pack_name is None

    def test_layer_content_pack(self) -> None:
        """Test pack layer content properties."""
        layer = LayerContent(content="# Pack", source="pack:python", path=Path("/pack/file.md"))

        assert layer.content == "# Pack"
        assert layer.source == "pack:python"
        assert layer.is_core is False
        assert layer.is_pack is True
        assert layer.is_project is False
        assert layer.pack_name == "python"

    def test_layer_content_project(self) -> None:
        """Test project layer content properties."""
        layer = LayerContent(content="# Project", source="project")

        assert layer.content == "# Project"
        assert layer.source == "project"
        assert layer.is_core is False
        assert layer.is_pack is False
        assert layer.is_project is True
        assert layer.pack_name is None

    def test_layer_content_optional_path(self) -> None:
        """Test layer content without path."""
        layer = LayerContent(content="# Test", source="core")

        assert layer.path is None
        assert layer.is_core is True


class TestCompositionContext:
    """Test CompositionContext dataclass."""

    def test_composition_context_minimal(self) -> None:
        """Test context with minimal required fields."""
        context = CompositionContext(
            active_packs=["python", "typescript"],
            config={"key": "value"},
        )

        assert context.active_packs == ["python", "typescript"]
        assert context.config == {"key": "value"}
        assert context.project_root is None
        assert context.source_dir is None

    def test_composition_context_full(self) -> None:
        """Test context with all fields."""
        project_root = Path("/project")
        source_dir = Path("/source")

        context = CompositionContext(
            active_packs=["python"],
            config={"enable_sections": True},
            project_root=project_root,
            source_dir=source_dir,
        )

        assert context.active_packs == ["python"]
        assert context.config == {"enable_sections": True}
        assert context.project_root == project_root
        assert context.source_dir == source_dir


class TestCompositionStrategy:
    """Test CompositionStrategy abstract base class."""

    def test_composition_strategy_is_abstract(self) -> None:
        """Test CompositionStrategy cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            CompositionStrategy()  # type: ignore

    def test_composition_strategy_requires_compose_method(self) -> None:
        """Test subclass must implement compose() method."""
        class IncompleteStrategy(CompositionStrategy):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteStrategy()  # type: ignore

    def test_composition_strategy_valid_subclass(self) -> None:
        """Test valid strategy implementation."""
        class ValidStrategy(CompositionStrategy):
            def compose(self, layers, context):
                return "composed"

        strategy = ValidStrategy()
        layers = [LayerContent(content="test", source="core")]
        context = CompositionContext(active_packs=[], config={})

        assert strategy.compose(layers, context) == "composed"
