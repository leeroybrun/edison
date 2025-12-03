"""Tests for CompositionFileWriter integration in all adapters.

Verifies that all sync and prompt adapters use CompositionFileWriter
for unified file writing instead of direct .write_text() calls.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from edison.core.adapters import CursorSync, ClaudeSync
from edison.core.adapters.prompt.cursor import CursorPromptAdapter
from edison.core.adapters.prompt.codex import CodexAdapter
from edison.core.adapters.prompt.zen import ZenPromptAdapter
from edison.core.adapters.sync.zen.client import ZenSync
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


class TestSyncAdaptersUseWriter:
    """Test that sync adapters use CompositionFileWriter property."""

    def test_cursor_sync_has_writer_property(self, isolated_project_env: Path) -> None:
        """CursorSync should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = CursorSync(project_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_claude_sync_has_writer_property(self, isolated_project_env: Path) -> None:
        """ClaudeSync should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = ClaudeSync(repo_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_zen_sync_has_writer_property(self, isolated_project_env: Path) -> None:
        """ZenSync should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)

        adapter = ZenSync(repo_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer


class TestPromptAdaptersUseWriter:
    """Test that prompt adapters use CompositionFileWriter property."""

    def test_cursor_prompt_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """CursorPromptAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)
        generated_root = root / ".edison" / "_generated"
        generated_root.mkdir(parents=True, exist_ok=True)

        adapter = CursorPromptAdapter(generated_root=generated_root, repo_root=root)

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
        generated_root = root / ".edison" / "_generated"
        generated_root.mkdir(parents=True, exist_ok=True)

        adapter = CodexAdapter(generated_root=generated_root, repo_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer

    def test_zen_prompt_adapter_has_writer_property(self, isolated_project_env: Path) -> None:
        """ZenPromptAdapter should have a lazy writer property."""
        root = isolated_project_env
        _write_minimal_config(root)
        generated_root = root / ".edison" / "_generated"
        generated_root.mkdir(parents=True, exist_ok=True)

        adapter = ZenPromptAdapter(generated_root=generated_root, repo_root=root)

        # Verify writer property exists
        assert hasattr(adapter, 'writer')
        writer = adapter.writer
        assert isinstance(writer, CompositionFileWriter)
        assert writer.base_dir == root

        # Verify writer is lazy and cached
        assert adapter.writer is writer


class TestAdaptersUseWriterForFileOperations:
    """Test that adapters use writer methods instead of direct write_text."""

    def test_cursor_sync_uses_writer_for_cursorrules(self, isolated_project_env: Path) -> None:
        """CursorSync should use writer.write_text for .cursorrules."""
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

        adapter = CursorSync(project_root=root)
        out_path = adapter.sync_to_cursorrules()

        # File should exist and have correct content
        assert out_path.exists()
        assert out_path.name == ".cursorrules"
        content = out_path.read_text(encoding="utf-8")
        assert "Test Rule" in content

    def test_claude_sync_uses_writer_for_agents(self, isolated_project_env: Path) -> None:
        """ClaudeSync should use writer.write_text for agent files."""
        root = isolated_project_env
        _write_minimal_config(root)

        # Create generated agent
        write_generated_agent(root, "test-agent", role_text="Test agent role.")

        adapter = ClaudeSync(repo_root=root)
        written = adapter.sync_agents()

        # Agent file should exist with frontmatter
        assert len(written) == 1
        agent_path = written[0]
        assert agent_path.exists()
        content = agent_path.read_text(encoding="utf-8")
        assert "name: test-agent" in content

    def test_cursor_prompt_adapter_uses_writer(self, isolated_project_env: Path) -> None:
        """CursorPromptAdapter should use writer for output files."""
        root = isolated_project_env
        _write_minimal_config(root)

        generated_root = root / ".edison" / "_generated"
        agents_dir = generated_root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Create test agent
        test_agent = agents_dir / "test-agent.md"
        test_agent.write_text("# Agent: test-agent\n\n## Role\nTest role.", encoding="utf-8")

        adapter = CursorPromptAdapter(generated_root=generated_root, repo_root=root)
        output_root = root / ".edison" / "_output" / "cursor"
        output_root.mkdir(parents=True, exist_ok=True)

        # This should use writer internally
        adapter.write_outputs(output_root)

        # Verify agent file was written
        agents_output = output_root / "cursor-agents" / "test-agent.md"
        assert agents_output.exists()
        content = agents_output.read_text(encoding="utf-8")
        assert "test-agent" in content
