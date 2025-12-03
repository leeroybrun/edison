"""Tests for CursorAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

CursorAdapter merges functionality from:
- adapters/prompt/cursor.py (CursorAdapter)
- adapters/sync/cursor.py (CursorSync)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters.platforms.cursor import CursorAdapter


def test_cursor_adapter_has_platform_name():
    """Test that CursorAdapter has correct platform_name."""
    adapter = CursorAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "cursor"


def test_cursor_adapter_has_sync_all():
    """Test that CursorAdapter implements sync_all method."""
    adapter = CursorAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_cursor_adapter_sync_cursorrules(tmp_path: Path):
    """Test syncing .cursorrules file."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    # Create minimal config to prevent errors
    config_dir = edison_dir / "config"
    config_dir.mkdir()
    composition_yaml = config_dir / "composition.yaml"
    composition_yaml.write_text("version: 1.0")

    adapter = CursorAdapter(project_root=project_root)
    result = adapter.sync_to_cursorrules()

    # Should create .cursorrules at project root
    assert result == project_root / ".cursorrules"
    assert result.exists()


def test_cursor_adapter_sync_agents(tmp_path: Path):
    """Test syncing agents to .cursor/agents/."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    # Create generated agent
    generated_agents = edison_dir / "_generated" / "agents"
    generated_agents.mkdir(parents=True)
    test_agent = generated_agents / "test-agent.md"
    test_agent.write_text("# Test Agent\n\nTest agent content")

    # Create .cursor directory
    cursor_dir = project_root / ".cursor"
    cursor_agents_dir = cursor_dir / "agents"
    cursor_agents_dir.mkdir(parents=True)

    adapter = CursorAdapter(project_root=project_root)
    synced = adapter.sync_agents_to_cursor()

    assert len(synced) == 1
    assert synced[0].name == "test-agent.md"
    assert synced[0].parent == cursor_agents_dir


def test_cursor_adapter_sync_structured_rules(tmp_path: Path):
    """Test syncing structured rules to .cursor/rules/."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    # Create .cursor directory
    cursor_dir = project_root / ".cursor"
    cursor_dir.mkdir()

    adapter = CursorAdapter(project_root=project_root)
    result = adapter.sync_structured_rules()

    # Should return list of paths (may be empty if no rules configured)
    assert isinstance(result, list)


def test_cursor_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary with synced paths."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = CursorAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict with expected keys
    assert isinstance(result, dict)
    assert "cursorrules" in result
    assert "rules" in result
    assert "agents" in result
    assert isinstance(result["cursorrules"], list)
    assert isinstance(result["rules"], list)
    assert isinstance(result["agents"], list)
