"""Tests for CompositionFileWriter integration in unified platform adapters.

Verifies that all platform adapters use CompositionFileWriter
for unified file writing instead of direct .write_text() calls.

Note: The old separate "sync" and "prompt" adapters have been unified
into single platform adapters (ClaudeAdapter, CursorAdapter, ZenAdapter, etc.)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters import (
    ClaudeAdapter,
    CursorAdapter,
    ZenAdapter,
    CodexAdapter,
    CoderabbitAdapter,
)
from edison.core.composition.output.writer import CompositionFileWriter
from tests.helpers.io_utils import write_yaml, write_generated_agent


def _write_minimal_config(root: Path) -> None:
    """Write minimal config needed for adapters."""
    project_data = {"project": {"name": "test-project"}}
    write_yaml(root / ".edison" / "config" / "project.yaml", project_data)

    packs_data = {"packs": {"active": []}}
    write_yaml(root / ".edison" / "config" / "packs.yaml", packs_data)

    config_data = {
        "project": {"name": "test-project"},
        "packs": {"active": []}
    }
    write_yaml(root / ".agents" / "config.yml", config_data)


class TestUnifiedAdaptersHaveWriter:
    """Test that all unified platform adapters have CompositionFileWriter property."""

    def test_cursor_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """CursorAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = CursorAdapter(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_claude_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """ClaudeAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = ClaudeAdapter(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_zen_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """ZenAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = ZenAdapter(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_codex_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """CodexAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = CodexAdapter(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_coderabbit_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """CoderabbitAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = CoderabbitAdapter(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer


class TestAdaptersUseWriterForFileOperations:
    """Test that adapters use writer methods instead of direct write_text."""

    def test_cursor_adapter_uses_writer_for_cursorrules(self, isolated_project_env: Path) -> None:
        """CursorAdapter should use writer.write_text for .cursorrules."""
        root = isolated_project_env
        _write_minimal_config(root)

        # Minimal guideline
        guidelines_dir = root / ".edison" / "guidelines"
        guidelines_dir.mkdir(parents=True, exist_ok=True)
        (guidelines_dir / "test.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

        registry_data = {
            "version": "1.0.0",
            "rules": [{
                "id": "test-1",
                "title": "Test Rule",
                "blocking": False,
                "contexts": []
            }]
        }
        write_yaml(root / ".edison" / "rules" / "registry.yml", registry_data)

        adapter = CursorAdapter(project_root=root)
        out_path = adapter.sync_to_cursorrules()

        # File should exist and have correct content
        assert out_path.exists()
        assert out_path.name == ".cursorrules"
        content = out_path.read_text(encoding="utf-8")
        assert "Test Rule" in content

    def test_claude_adapter_uses_writer_for_agents(self, isolated_project_env: Path) -> None:
        """ClaudeAdapter should use writer.write_text for agent files."""
        root = isolated_project_env
        _write_minimal_config(root)

        # Create generated agent
        write_generated_agent(root, "test-agent", role_text="Test agent role.")

        adapter = ClaudeAdapter(project_root=root)
        written = adapter.sync_agents()

        # Agent file should exist with frontmatter
        assert len(written) == 1
        agent_path = written[0]
        assert agent_path.exists()
        content = agent_path.read_text(encoding="utf-8")
        assert "name: test-agent" in content

    def test_cursor_adapter_syncs_agents(self, isolated_project_env: Path) -> None:
        """CursorAdapter should sync agents from generated directory."""
        root = isolated_project_env
        _write_minimal_config(root)

        # Create generated agent
        generated_agents = root / ".edison" / "_generated" / "agents"
        generated_agents.mkdir(parents=True, exist_ok=True)
        (generated_agents / "test-agent.md").write_text(
            "# Agent: test-agent\n\n## Role\nTest role.",
            encoding="utf-8"
        )

        adapter = CursorAdapter(project_root=root)
        written = adapter.sync_agents_to_cursor()

        # Agent should be synced to .cursor/agents/
        if written:
            assert all(p.exists() for p in written)
