"""Tests for Claude Code adapter."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from edison.core.adapters import ClaudeAdapter
from edison.core.adapters import load_schema
from tests.helpers.io_utils import (
    write_generated_agent,
    write_orchestrator_constitution,
    write_orchestrator_manifest,
    write_yaml,
)

# Repository root for test fixtures
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestClaudeAdapterUnit:
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

        # Parse YAML frontmatter (avoid asserting on specific markdown headings/phrasing).
        assert content.startswith("---\n")
        _, fm_text, body = content.split("---", 2)
        frontmatter = yaml.safe_load(fm_text)
        assert frontmatter["name"] == "feature-implementer"
        assert frontmatter["description"] == "Full-stack feature orchestrator."
        assert body.strip()

        # Source remains untouched
        assert src.read_text(encoding="utf-8").startswith("# Agent: feature-implementer")


class TestClaudeAdapterCommands:
    def test_sync_all_writes_only_claude_commands(self, isolated_project_env: Path) -> None:
        root = isolated_project_env

        # Force-enable codex + cursor in platforms and point codex output inside the project
        # so we can detect accidental cross-platform writes.
        (root / ".edison" / "config").mkdir(parents=True, exist_ok=True)
        write_yaml(
            root / ".edison" / "config" / "commands.yaml",
            {
                "commands": {
                    "platforms": ["claude", "cursor", "codex"],
                    "platform_config": {
                        "codex": {"enabled": True, "output_dir": str(root / ".codex" / "prompts")},
                        "cursor": {"enabled": True, "output_dir": str(root / ".cursor" / "commands")},
                        "claude": {"enabled": True, "output_dir": str(root / ".claude" / "commands")},
                    },
                }
            },
        )

        # Seed at least one generated agent so adapter has something to sync.
        write_generated_agent(root, "demo", role_text="demo")

        adapter = ClaudeAdapter(project_root=root)
        result = adapter.sync_all()

        # Claude commands should be written
        assert any((root / ".claude" / "commands").glob("*.md"))
        assert result.get("commands")

        # Other platform command dirs must NOT be written by claude adapter.
        assert not (root / ".cursor" / "commands").exists()
        assert not (root / ".codex" / "prompts").exists()
