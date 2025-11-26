"""Tests for Claude Code adapter."""
from __future__ import annotations

import json
import shutil
import time
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
        """Create a minimal Edison-composed agent in .agents/_generated/agents."""
        agents_dir = root / ".agents" / "_generated" / "agents"
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
        out_dir = root / ".agents" / "_generated" / "constitutions"
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
        out_dir = root / ".agents" / "_generated"
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
        """validate_claude_structure creates .claude and agents subdir when missing."""
        root = isolated_project_env
        adapter = ClaudeSync(repo_root=root)

        claude_dir = adapter.validate_claude_structure()

        assert claude_dir == root / ".claude"
        assert claude_dir.exists()
        assert (claude_dir / "agents").exists()

    def test_agent_conversion_preserves_sections(self, isolated_project_env: Path) -> None:
        """sync_agents_to_claude converts Edison agents into Claude agent files."""
        root = isolated_project_env
        src = self._write_generated_agent(root, "feature-implementer", role_text="Full-stack feature orchestrator.")

        adapter = ClaudeSync(repo_root=root)
        changed = adapter.sync_agents_to_claude()

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

    def test_sync_agents_to_claude_is_incremental(self, isolated_project_env: Path) -> None:
        """Running sync twice without changes does not rewrite agent files."""
        root = isolated_project_env
        self._write_generated_agent(root, "api-builder", role_text="Backend API specialist.")

        adapter = ClaudeSync(repo_root=root)

        first_changed = adapter.sync_agents_to_claude()
        assert len(first_changed) == 1

        dest = root / ".claude" / "agents" / "api-builder.md"
        assert dest.exists()
        mtime_first = dest.stat().st_mtime

        # Slight delay to ensure filesystem timestamp resolution is not a factor
        time.sleep(0.01)

        second_changed = adapter.sync_agents_to_claude()
        assert second_changed == []
        mtime_second = dest.stat().st_mtime
        assert mtime_second == pytest.approx(mtime_first)

    def test_sync_orchestrator_appends_constitution(self, isolated_project_env: Path) -> None:
        """sync_orchestrator_to_claude appends orchestrator constitution into CLAUDE.md."""
        root = isolated_project_env
        claude_dir = root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text(
            "\n".join(
                [
                    "# Claude Code Orchestrator",
                    "<!-- GENERATED - DO NOT EDIT -->",
                    "",
                    "# Claude Orchestrator Brief",
                    "Existing orchestrator content.",
                ]
            ),
            encoding="utf-8",
        )
        constitution = self._write_orchestrator_constitution(root)

        adapter = ClaudeSync(repo_root=root)
        out_path = adapter.sync_orchestrator_to_claude()

        assert out_path == claude_md
        content = claude_md.read_text(encoding="utf-8")
        # Existing content preserved
        assert "# Claude Orchestrator Brief" in content
        # Constitution content injected with clear markers
        assert constitution.read_text(encoding="utf-8").splitlines()[0] in content
        assert "<!-- EDISON_ORCHESTRATOR_GUIDE_START -->" in content
        assert "<!-- EDISON_ORCHESTRATOR_GUIDE_END -->" in content

    def test_generate_claude_config_uses_manifest_agents(self, isolated_project_env: Path) -> None:
        """generate_claude_config writes config.json with active agent roster from manifest."""
        root = isolated_project_env
        self._write_orchestrator_manifest(root)
        claude_dir = root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "agents").mkdir(exist_ok=True)

        adapter = ClaudeSync(repo_root=root)
        config_path = adapter.generate_claude_config()

        assert config_path == claude_dir / "config.json"
        assert config_path.exists()

        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["version"] == "2.0.0"
        assert data["orchestratorManifest"] == ".agents/_generated/orchestrator-manifest.json"
        assert data["agents"]["generic"] == ["feature-implementer"]
        assert sorted(data["agents"]["specialized"]) == ["api-builder", "component-builder-nextjs"]
        assert data["agents"]["project"] == ["custom-agent"]
        # Default agent should favor feature-implementer when present
        assert data["defaultAgent"] == "feature-implementer"

    def test_sync_agents_invalid_structure_fails_schema(self, isolated_project_env: Path) -> None:
        """Agents missing Role content should fail Claude agent schema validation."""
        root = isolated_project_env
        self._install_schemas(root)
        self._install_schemas(root)

        # Write a generated agent with an empty Role section
        agents_dir = root / ".agents" / "_generated" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        bad_agent = agents_dir / "broken-agent.md"
        bad_agent.write_text(
            "\n".join(
                [
                    "# Agent: broken-agent",
                    "",
                    "## Role",
                    "",
                    "## Tools",
                    "- tool-one",
                    "",
                    "## Guidelines",
                    "- guideline-one",
                    "",
                    "## Workflows",
                    "- workflow-one",
                ]
            ),
            encoding="utf-8",
        )

        adapter = ClaudeSync(repo_root=root)
        # Sanity check: jsonschema and schema are available
        import edison.core.adapters._schemas as schemas_mod  # type: ignore

        assert schemas_mod.jsonschema is not None  # type: ignore[attr-defined]
        assert load_schema("claude-agent.schema.json", repo_root=root), "claude-agent.schema.json schema not loaded"

        text = bad_agent.read_text(encoding="utf-8")
        sections = adapter._parse_edison_agent(text, fallback_name="broken-agent")
        payload = adapter._build_agent_payload(sections, {})
        assert payload["sections"]["role"] == ""

        # Direct jsonschema validation should fail for the empty Role
        with pytest.raises(Exception) as excinfo:
            adapter._validate_agent_payload("broken-agent", payload)

        msg = str(excinfo.value)
        assert "schema" in msg.lower() or "validation" in msg.lower()

    def test_agent_config_overrides_and_schema_validation(self, isolated_project_env: Path) -> None:
        """Per-agent JSON config overrides frontmatter and is validated against schema."""
        root = isolated_project_env
        self._install_schemas(root)
        self._write_generated_agent(root, "feature-implementer", role_text="Base role.")

        cfg_dir = root / ".agents" / "claude" / "agents"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg = {
            "name": "feature-implementer-override",
            "description": "Custom description from config.",
            "model": "haiku",
            "tags": ["fullstack", "priority"],
            "enabled": True,
        }
        (cfg_dir / "feature-implementer.json").write_text(json.dumps(cfg), encoding="utf-8")

        adapter = ClaudeSync(repo_root=root)
        # Sanity check: schema must be available for validation
        assert load_schema("claude-agent-config.schema.json", repo_root=root), "claude-agent-config.schema.json schema not loaded"
        changed = adapter.sync_agents_to_claude()

        assert len(changed) == 1
        claude_agent = root / ".claude" / "agents" / "feature-implementer.md"
        content = claude_agent.read_text(encoding="utf-8")

        assert "name: feature-implementer-override" in content
        assert "description: Custom description from config." in content
        assert "model: haiku" in content
        assert "tags:" in content

    def test_agent_config_invalid_schema_raises(self, isolated_project_env: Path) -> None:
        """Invalid per-agent config (wrong types) is rejected by schema validation."""
        root = isolated_project_env
        self._install_schemas(root)
        self._write_generated_agent(root, "feature-implementer", role_text="Base role.")

        cfg_dir = root / ".agents" / "claude" / "agents"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        # Invalid: model must be string, not number
        bad_cfg = {"model": 123}
        (cfg_dir / "feature-implementer.json").write_text(json.dumps(bad_cfg), encoding="utf-8")

        adapter = ClaudeSync(repo_root=root)
        with pytest.raises(Exception) as excinfo:
            adapter._validate_agent_config("feature-implementer", bad_cfg)

        msg = str(excinfo.value)
        assert "schema" in msg.lower() or "validation" in msg.lower()
