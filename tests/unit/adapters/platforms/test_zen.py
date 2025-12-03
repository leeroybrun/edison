"""Tests for ZenAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

ZenAdapter is based on:
- adapters/sync/zen/client.py (ZenSync)
- adapters/sync/zen/composer.py (ZenComposerMixin)
- adapters/sync/zen/discovery.py (ZenDiscoveryMixin)
- adapters/sync/zen/sync.py (ZenSyncMixin)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters.platforms.zen import ZenAdapter


def test_zen_adapter_has_platform_name():
    """Test that ZenAdapter has correct platform_name."""
    adapter = ZenAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "zen"


def test_zen_adapter_has_sync_all():
    """Test that ZenAdapter implements sync_all method."""
    adapter = ZenAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_zen_adapter_has_mixin_methods():
    """Test that ZenAdapter has methods from mixins."""
    adapter = ZenAdapter(project_root=Path.cwd())

    # Should have methods from ZenComposerMixin
    assert hasattr(adapter, "compose_zen_prompt")

    # Should have methods from ZenDiscoveryMixin
    assert hasattr(adapter, "get_applicable_guidelines")
    assert hasattr(adapter, "get_applicable_rules")

    # Should have methods from ZenSyncMixin
    assert hasattr(adapter, "sync_role_prompts")


def test_zen_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = ZenAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict (structure depends on Zen config)
    assert isinstance(result, dict)
