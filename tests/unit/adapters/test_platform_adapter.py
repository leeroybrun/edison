"""Tests for PlatformAdapter base class.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import pytest

from edison.core.adapters.base import PlatformAdapter


class ConcretePlatformAdapter(PlatformAdapter):
    """Concrete implementation for testing."""

    @property
    def platform_name(self) -> str:
        return "test_platform"

    def sync_all(self) -> Dict[str, Any]:
        return {"synced": True}


def test_platform_adapter_has_platform_name():
    """Test that PlatformAdapter requires platform_name property."""
    adapter = ConcretePlatformAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "test_platform"


def test_platform_adapter_has_sync_all():
    """Test that PlatformAdapter requires sync_all method."""
    adapter = ConcretePlatformAdapter(project_root=Path.cwd())
    result = adapter.sync_all()
    assert result == {"synced": True}


def test_platform_adapter_inherits_from_composition_base():
    """Test that PlatformAdapter extends CompositionBase."""
    adapter = ConcretePlatformAdapter(project_root=Path.cwd())

    # Should have CompositionBase attributes
    assert hasattr(adapter, "project_root")
    assert hasattr(adapter, "project_dir")
    assert hasattr(adapter, "config")
    assert hasattr(adapter, "cfg_mgr")
    assert hasattr(adapter, "writer")


def test_platform_adapter_has_adapters_config():
    """Test that PlatformAdapter provides adapters_config property."""
    adapter = ConcretePlatformAdapter(project_root=Path.cwd())

    # Should have adapters_config (from SyncAdapter pattern)
    assert hasattr(adapter, "adapters_config")
    adapters_cfg = adapter.adapters_config
    assert adapters_cfg is not None


def test_platform_adapter_has_output_config():
    """Test that PlatformAdapter provides output_config property."""
    adapter = ConcretePlatformAdapter(project_root=Path.cwd())

    # Should have output_config (from SyncAdapter pattern)
    assert hasattr(adapter, "output_config")
    output_cfg = adapter.output_config
    assert output_cfg is not None


def test_platform_adapter_cannot_instantiate_without_abstract_methods():
    """Test that PlatformAdapter cannot be instantiated without implementing abstract methods."""

    class IncompletePlatformAdapter(PlatformAdapter):
        """Incomplete adapter missing abstract methods."""
        pass

    with pytest.raises(TypeError) as exc_info:
        IncompletePlatformAdapter(project_root=Path.cwd())  # type: ignore[abstract]

    assert "abstract" in str(exc_info.value).lower()


def test_platform_adapter_sync_agents_from_generated(tmp_path: Path):
    """Test sync_agents_from_generated helper method."""
    # Setup test structure
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    generated_agents = edison_dir / "_generated" / "agents"
    generated_agents.mkdir(parents=True)

    # Create test agent file
    test_agent = generated_agents / "test-agent.md"
    test_agent.write_text("# Test Agent\n\nThis is a test agent.")

    # Create adapter and sync
    adapter = ConcretePlatformAdapter(project_root=project_root)
    target_dir = tmp_path / "output" / "agents"

    synced = adapter.sync_agents_from_generated(target_dir)

    assert len(synced) == 1
    assert synced[0].name == "test-agent.md"
    assert synced[0].parent == target_dir
    assert synced[0].read_text() == "# Test Agent\n\nThis is a test agent."
