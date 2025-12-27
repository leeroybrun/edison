"""Tests for PalAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

PalAdapter uses the platform adapter mixin pattern for prompt composition/sync.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters.platforms.pal import PalAdapter


def test_pal_adapter_has_platform_name():
    """Test that PalAdapter has correct platform_name."""
    adapter = PalAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "pal"


def test_pal_adapter_has_sync_all():
    """Test that PalAdapter implements sync_all method."""
    adapter = PalAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_pal_adapter_has_mixin_methods():
    """Test that PalAdapter has methods from mixins."""
    adapter = PalAdapter(project_root=Path.cwd())

    # Should have methods from PalComposerMixin
    assert hasattr(adapter, "compose_pal_prompt")

    # Should have methods from PalDiscoveryMixin
    assert hasattr(adapter, "get_applicable_guidelines")
    assert hasattr(adapter, "get_applicable_rules")

    # Should have methods from PalSyncMixin
    assert hasattr(adapter, "sync_role_prompts")


def test_pal_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = PalAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict (structure depends on Pal config)
    assert isinstance(result, dict)
