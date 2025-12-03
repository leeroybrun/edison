"""Tests for CodexAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

CodexAdapter is based on:
- adapters/prompt/codex.py (CodexAdapter)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters.platforms.codex import CodexAdapter


def test_codex_adapter_has_platform_name():
    """Test that CodexAdapter has correct platform_name."""
    adapter = CodexAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "codex"


def test_codex_adapter_has_sync_all():
    """Test that CodexAdapter implements sync_all method."""
    adapter = CodexAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_codex_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary with synced paths."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = CodexAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict (Codex is simpler, may just have empty structure)
    assert isinstance(result, dict)
