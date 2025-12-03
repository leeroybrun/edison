"""Tests for ComposableGenerator base class.

Following strict TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from edison.core.composition.generators.base import ComposableGenerator


class ConcreteGenerator(ComposableGenerator):
    """Concrete implementation for testing."""

    @property
    def template_name(self) -> str:
        return "TEST_TEMPLATE"

    @property
    def output_filename(self) -> str:
        return "test_output.md"

    def _gather_data(self) -> Dict[str, Any]:
        return {
            "test_key": "test_value",
            "items": ["item1", "item2"],
        }


def test_composable_generator_has_content_type():
    """Test that ComposableGenerator has generators content_type."""
    generator = ConcreteGenerator()
    assert generator.content_type == "generators"


def test_composable_generator_requires_template_name():
    """Test that subclasses must implement template_name property."""
    class MissingTemplate(ComposableGenerator):
        @property
        def output_filename(self) -> str:
            return "output.md"

        def _gather_data(self) -> Dict[str, Any]:
            return {}

    # Cannot instantiate abstract class without implementing template_name
    with pytest.raises(TypeError, match="abstract"):
        MissingTemplate()


def test_composable_generator_requires_output_filename():
    """Test that subclasses must implement output_filename property."""
    class MissingFilename(ComposableGenerator):
        @property
        def template_name(self) -> str:
            return "TEMPLATE"

        def _gather_data(self) -> Dict[str, Any]:
            return {}

    # Cannot instantiate abstract class without implementing output_filename
    with pytest.raises(TypeError, match="abstract"):
        MissingFilename()


def test_composable_generator_requires_gather_data():
    """Test that subclasses must implement _gather_data method."""
    class MissingGatherData(ComposableGenerator):
        @property
        def template_name(self) -> str:
            return "TEMPLATE"

        @property
        def output_filename(self) -> str:
            return "output.md"

    # Cannot instantiate abstract class without implementing _gather_data
    with pytest.raises(TypeError, match="abstract"):
        MissingGatherData()


def test_composable_generator_inherits_from_composition_base(tmp_path: Path):
    """Test that ComposableGenerator inherits from CompositionBase."""
    generator = ConcreteGenerator(project_root=tmp_path)

    # Should have CompositionBase properties
    assert hasattr(generator, "project_root")
    assert hasattr(generator, "project_dir")
    assert hasattr(generator, "cfg_mgr")
    assert hasattr(generator, "config")
    assert hasattr(generator, "writer")
    assert generator.project_root == tmp_path


def test_composable_generator_generate_method_exists():
    """Test that generate() method exists."""
    generator = ConcreteGenerator()
    assert hasattr(generator, "generate")
    assert callable(generator.generate)


def test_composable_generator_write_method_exists():
    """Test that write() method exists."""
    generator = ConcreteGenerator()
    assert hasattr(generator, "write")
    assert callable(generator.write)


def test_composable_generator_write_creates_file(tmp_path: Path):
    """Test that write() creates output file."""
    # Create a simple generator that doesn't need templates
    class SimpleGenerator(ComposableGenerator):
        @property
        def template_name(self) -> str:
            return None  # No template needed

        @property
        def output_filename(self) -> str:
            return "simple.md"

        def _gather_data(self) -> Dict[str, Any]:
            return {"title": "Test"}

        def generate(self) -> str:
            # Override to skip template composition
            return "# Test Content\n\nGenerated successfully."

    generator = SimpleGenerator(project_root=tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result_path = generator.write(output_dir)

    assert result_path.exists()
    assert result_path == output_dir / "simple.md"
    assert "Test Content" in result_path.read_text()


def test_composable_generator_has_compose_template_helper():
    """Test that _compose_template() helper exists for template composition."""
    generator = ConcreteGenerator()
    assert hasattr(generator, "_compose_template")
    assert callable(generator._compose_template)


def test_composable_generator_has_inject_data_helper():
    """Test that _inject_data() helper exists for data injection."""
    generator = ConcreteGenerator()
    assert hasattr(generator, "_inject_data")
    assert callable(generator._inject_data)
