"""Tests for CoderabbitAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

CoderabbitAdapter is based on:
- composition/ide/coderabbit.py (CoderabbitAdapter)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters import CoderabbitAdapter


def test_coderabbit_adapter_has_platform_name():
    """Test that CoderabbitAdapter has correct platform_name."""
    adapter = CoderabbitAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "coderabbit"


def test_coderabbit_adapter_has_sync_all():
    """Test that CoderabbitAdapter implements sync_all method."""
    adapter = CoderabbitAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_coderabbit_adapter_compose_config(tmp_path: Path):
    """Test composing CodeRabbit configuration."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = CoderabbitAdapter(project_root=project_root)
    config = adapter.compose_coderabbit_config()

    # Should return a dict (even if empty)
    assert isinstance(config, dict)


def test_coderabbit_adapter_write_config(tmp_path: Path):
    """Test writing .coderabbit.yaml file."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = CoderabbitAdapter(project_root=project_root)
    written_path = adapter.write_coderabbit_config()

    # Should write to project root by default
    assert written_path.name == ".coderabbit.yaml"
    assert written_path.exists()


def test_coderabbit_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary with synced paths."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = CoderabbitAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict with config key
    assert isinstance(result, dict)
    assert "config" in result
