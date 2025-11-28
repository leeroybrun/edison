"""Tests for Claude Code adapter."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from edison.core.adapters import ClaudeSync
from edison.core.adapters import load_schema

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

    def _write_generated_agent(self, root: Path, name: str, role_text: str = "") -> Path:
        """Create a minimal Edison-composed agent in .edison/_generated/agents."""
        agents_dir = root / ".edison" / "_generated" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        path = agents_dir / f"{name}.md"
        content_lines = [
            f"# Agent: {name}",
            "",
            "## Role",
            role_text or f"Core role for {name}.",
            "",
            "## Tools",
            "- tool-one",
            "- tool-two",
            "",
            "## Guidelines",
            "- follow the rules",
            "",
            "## Workflows",
            "- do the work",
        ]
        path.write_text("\n".join(content_lines), encoding="utf-8")
        return path

    def _write_orchestrator_constitution(self, root: Path) -> Path:
        """Write orchestrator constitution (replaces ORCHESTRATOR_GUIDE.md - T-011)."""
        out_dir = root / ".edison" / "_generated" / "constitutions"
        out_dir.mkdir(parents=True, exist_ok=True)
        constitution = out_dir / "ORCHESTRATORS.md"
        constitution.write_text(
            "\n".join(
                [
                    "# Test Orchestrator Constitution",
                    "",
                    "## 📋 Mandatory Preloads (Session Start)",
                    "- SESSION_WORKFLOW.md",
                ]
            ),
            encoding="utf-8",
        )
        return constitution

    def _write_orchestrator_manifest(self, root: Path) -> Path:
        out_dir = root / ".edison" / "_generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = out_dir / "orchestrator-manifest.json"
        data = {
            "version": "2.0.0",
            "generated": "2025-01-01T00:00:00",
            "composition": {"packs": [], "guidelinesCount": 0, "validatorsCount": 0, "agentsCount": 3},
            "validators": {"global": [], "critical": [], "specialized": []},
            "agents": {
                "generic": ["feature-implementer"],
                "specialized": ["api-builder", "component-builder-nextjs"],
                "project": ["custom-agent"],
            },
            "guidelines": [],
            "delegation": {"filePatterns": {}, "taskTypes": {}},
            "workflowLoop": {},
        }
        manifest.write_text(json.dumps(data), encoding="utf-8")
        return manifest

    def test_validate_claude_structure_creates_dirs(self, isolated_project_env: Path) -> None:
        """validate_structure creates .claude and agents subdir when missing."""
        root = isolated_project_env
        adapter = ClaudeSync(repo_root=root)

        claude_dir = adapter.validate_structure()

        assert claude_dir == root / ".claude"
        assert claude_dir.exists()
        assert (claude_dir / "agents").exists()

    def test_agent_conversion_preserves_sections(self, isolated_project_env: Path) -> None:
        """sync_agents converts Edison agents into Claude agent files."""
        root = isolated_project_env
        src = self._write_generated_agent(root, "feature-implementer", role_text="Full-stack feature orchestrator.")

        adapter = ClaudeSync(repo_root=root)
        changed = adapter.sync_agents()

        claude_agent = root / ".claude" / "agents" / "feature-implementer.md"
        assert claude_agent in changed
        content = claude_agent.read_text(encoding="utf-8")

        # Frontmatter metadata
        assert content.startswith("name: feature-implementer")
        assert "description: Full-stack feature orchestrator." in content
        # Body still contains key sections from Edison agent
        assert "# Agent: feature-implementer" in content
        assert "## Role" in content
        assert "## Tools" in content
        assert "## Guidelines" in content
        assert "## Workflows" in content

        # Source remains untouched
        assert src.read_text(encoding="utf-8").startswith("# Agent: feature-implementer")

