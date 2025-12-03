"""Tests for AdapterComponent base class.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import pytest

from edison.core.adapters.components.base import AdapterComponent
from edison.core.adapters.base import PlatformAdapter


class MockPlatformAdapter(PlatformAdapter):
    """Mock platform adapter for component testing."""

    @property
    def platform_name(self) -> str:
        return "test"

    def sync_all(self) -> Dict[str, Any]:
        return {}


class ConcreteComponent(AdapterComponent):
    """Concrete component for testing."""

    def compose(self) -> str:
        return "composed content"

    def sync(self, output_dir: Path) -> List[Path]:
        target = output_dir / "test.md"
        self.writer.write_text(target, "test content")
        return [target]


def test_adapter_component_requires_adapter():
    """Test that AdapterComponent requires an adapter instance."""
    adapter = MockPlatformAdapter(project_root=Path.cwd())
    component = ConcreteComponent(adapter.context)

    assert component.adapter is adapter


def test_adapter_component_provides_config_access():
    """Test that AdapterComponent provides access to adapter config."""
    adapter = MockPlatformAdapter(project_root=Path.cwd())
    component = ConcreteComponent(adapter.context)

    # Should have config from adapter
    assert component.config is not None
    assert component.config == adapter.config


def test_adapter_component_provides_writer_access():
    """Test that AdapterComponent provides access to adapter writer."""
    adapter = MockPlatformAdapter(project_root=Path.cwd())
    component = ConcreteComponent(adapter.context)

    # Should have writer from adapter
    assert component.writer is not None
    assert component.writer is adapter.writer


def test_adapter_component_compose_method():
    """Test that AdapterComponent has compose method."""
    adapter = MockPlatformAdapter(project_root=Path.cwd())
    component = ConcreteComponent(adapter.context)

    result = component.compose()
    assert result == "composed content"


def test_adapter_component_sync_method(tmp_path: Path):
    """Test that AdapterComponent has sync method."""
    adapter = MockPlatformAdapter(project_root=tmp_path)
    component = ConcreteComponent(adapter.context)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    synced = component.sync(output_dir)

    assert len(synced) == 1
    assert synced[0].name == "test.md"
    assert synced[0].read_text() == "test content"


def test_adapter_component_cannot_instantiate_without_abstract_methods():
    """Test that AdapterComponent cannot be instantiated without implementing abstract methods."""

    class IncompleteComponent(AdapterComponent):
        """Incomplete component missing abstract methods."""
        pass

    adapter = MockPlatformAdapter(project_root=Path.cwd())

    with pytest.raises(TypeError) as exc_info:
        IncompleteComponent(adapter)  # type: ignore[abstract]

    assert "abstract" in str(exc_info.value).lower()
