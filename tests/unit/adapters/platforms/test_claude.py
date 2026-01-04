"""Tests for ClaudeAdapter platform adapter.

Following STRICT TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor

ClaudeAdapter merges functionality from:
- adapters/sync/claude.py (ClaudeAdapter)
- adapters/prompt/claude.py (ClaudeAdapter)
"""
from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from edison.core.adapters.platforms.claude import ClaudeAdapter


def test_claude_adapter_has_platform_name():
    """Test that ClaudeAdapter has correct platform_name."""
    adapter = ClaudeAdapter(project_root=Path.cwd())
    assert adapter.platform_name == "claude"


def test_claude_adapter_has_sync_all():
    """Test that ClaudeAdapter implements sync_all method."""
    adapter = ClaudeAdapter(project_root=Path.cwd())

    # Should have sync_all method
    assert hasattr(adapter, "sync_all")
    assert callable(adapter.sync_all)


def test_claude_adapter_sync_claude_md(tmp_path: Path):
    """Test syncing CLAUDE.md client config."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    # Create generated client file
    generated_clients = edison_dir / "_generated" / "clients"
    generated_clients.mkdir(parents=True)
    claude_md = generated_clients / "claude.md"
    claude_md.write_text("# Claude Config\n\nTest config")

    # Create .claude directory
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()

    adapter = ClaudeAdapter(project_root=project_root)
    result = adapter.sync_claude_md()

    # Should sync to .claude/CLAUDE.md
    assert result is not None
    assert result.name == "CLAUDE.md"
    assert result.parent == claude_dir
    assert "# Claude Config\n\nTest config" in result.read_text(encoding="utf-8")


def test_claude_adapter_sync_agents_with_frontmatter(tmp_path: Path):
    """Test syncing agents with Claude frontmatter."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    # Create generated agent
    generated_agents = edison_dir / "_generated" / "agents"
    generated_agents.mkdir(parents=True)
    test_agent = generated_agents / "test-agent.md"
    test_agent.write_text("# Test Agent\n\nTest agent content")

    # Create .claude directory
    claude_dir = project_root / ".claude"
    claude_agents_dir = claude_dir / "agents"
    claude_agents_dir.mkdir(parents=True)

    adapter = ClaudeAdapter(project_root=project_root)
    synced = adapter.sync_agents()

    assert len(synced) == 1
    assert synced[0].name == "test-agent.md"

    # Should have frontmatter
    content = synced[0].read_text()
    assert content.startswith("---")
    _, fm_text, body = content.split("---", 2)
    frontmatter = yaml.safe_load(fm_text)
    assert frontmatter["name"] == "test-agent"
    assert isinstance(frontmatter.get("model"), str)
    assert body.strip()


def test_claude_adapter_sync_all_returns_dict(tmp_path: Path):
    """Test that sync_all returns dictionary with synced paths."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    edison_dir = project_root / ".edison"
    edison_dir.mkdir()

    adapter = ClaudeAdapter(project_root=project_root)
    result = adapter.sync_all()

    # Should return dict with expected keys
    assert isinstance(result, dict)
    assert "claude_md" in result
    assert "agents" in result
    assert isinstance(result["claude_md"], list)
    assert isinstance(result["agents"], list)
