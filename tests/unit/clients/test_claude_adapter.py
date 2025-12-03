"""Tests for Claude Code adapter."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from edison.core.adapters import ClaudeAdapter
from edison.core.adapters import load_schema
from tests.helpers.io_utils import write_generated_agent, write_orchestrator_constitution, write_orchestrator_manifest

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestClaudeAdapterUnit:
    def _install_schemas(self, root: Path) -> None:
        """Copy core Claude schemas into the isolated project."""
        # Schemas are in the edison package data directory
        schema_src_dir = REPO_ROOT / "src" / "edison" / "data" / "schemas"
        schema_dst_dir = root / ".edison" / "core" / "schemas"
        schema_dst_dir.mkdir(parents=True, exist_ok=True)
        for name in ("claude-agent.schema.json", "claude-agent-config.schema.json"):
            src = schema_src_dir / name
            if src.exists():
                shutil.copy(src, schema_dst_dir / name)

    def test_validate_claude_structure_creates_dirs(self, isolated_project_env: Path) -> None:
        """validate_structure creates .claude and agents subdir when missing."""
        root = isolated_project_env
        adapter = ClaudeAdapter(project_root=root)

        claude_dir = adapter.validate_structure()

        assert claude_dir == root / ".claude"
        assert claude_dir.exists()
        assert (claude_dir / "agents").exists()

    def test_agent_conversion_preserves_sections(self, isolated_project_env: Path) -> None:
        """sync_agents converts Edison agents into Claude agent files."""
        root = isolated_project_env
        src = write_generated_agent(root, "feature-implementer", role_text="Full-stack feature orchestrator.")

        adapter = ClaudeAdapter(project_root=root)
        changed = adapter.sync_agents()

        claude_agent = root / ".claude" / "agents" / "feature-implementer.md"
        assert claude_agent in changed
        content = claude_agent.read_text(encoding="utf-8")

        # Frontmatter metadata (YAML format with --- delimiters)
        assert content.startswith("---\nname: feature-implementer")
        assert "description: Full-stack feature orchestrator." in content
        # Body still contains key sections from Edison agent
        assert "# Agent: feature-implementer" in content
        assert "## Role" in content
        assert "## Tools" in content
        assert "## Guidelines" in content
        assert "## Workflows" in content

        # Source remains untouched
        assert src.read_text(encoding="utf-8").startswith("# Agent: feature-implementer")

