from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import json
import os

import pytest
from edison.core.utils.subprocess import run_with_timeout


_CUR = Path(__file__).resolve()
CORE_ROOT = None
for parent in _CUR.parents:
    if (parent / "lib" / "composition" / "__init__.py").exists():
        CORE_ROOT = parent
        break

assert CORE_ROOT is not None, "cannot locate Edison core lib root"

REPO_ROOT = CORE_ROOT.parents[1]


def _bootstrap_minimal_project(root: Path) -> None:
    """Populate isolated project root with minimal Edison config/layout."""
    # .edison/core defaults.yaml (copy from real repo)
    core_dir = root / ".edison" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    real_defaults = REPO_ROOT / ".edison" / "core" / "defaults.yaml"
    if real_defaults.exists():
        shutil.copy(real_defaults, core_dir / "defaults.yaml")
    else:
        # Minimal fallback configuration when defaults not present
        (core_dir / "defaults.yaml").write_text(
            "validation:\n  roster:\n    global: []\n    critical: []\n    specialized: []\n",
            encoding="utf-8",
        )

    # Project config.yml (copy from real repo)
    agents_dir = root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    real_config = REPO_ROOT / ".agents" / "config.yml"
    if real_config.exists():
        shutil.copy(real_config, agents_dir / "config.yml")
    else:
        (agents_dir / "config.yml").write_text("project:\n  name: test-project\n", encoding="utf-8")


class TestClaudeIntegrationE2E:
    def _write_generated_agent(self, root: Path, name: str) -> None:
        gen_dir = root / ".agents" / "_generated" / "agents"
        gen_dir.mkdir(parents=True, exist_ok=True)
        gen_dir.joinpath(f"{name}.md").write_text(
            "\n".join(
                [
                    f"# Agent: {name}",
                    "",
                    "## Role",
                    f"Role for {name}.",
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

    def _write_manifest(self, root: Path, agents: dict[str, list[str]]) -> None:
        out_dir = root / ".agents" / "_generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": "2.0.0",
            "generated": "2025-01-01T00:00:00",
            "composition": {"packs": [], "guidelinesCount": 0, "validatorsCount": 0, "agentsCount": sum(len(v) for v in agents.values())},
            "validators": {"global": [], "critical": [], "specialized": []},
            "agents": agents,
            "guidelines": [],
            "delegation": {"filePatterns": {}, "taskTypes": {}},
            "workflowLoop": {},
        }
        (out_dir / "orchestrator-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    @pytest.mark.integration
    def test_full_sync_pipeline_via_cli(self, isolated_project_env: Path) -> None:
        """compose --sync-claude syncs agents, orchestrator guide, and config.json into .claude/."""
        root = isolated_project_env
        _bootstrap_minimal_project(root)

        # Generated Edison artifacts
        self._write_generated_agent(root, "api-builder")
        self._write_generated_agent(root, "component-builder-nextjs")
        self._write_manifest(
            root,
            {
                "generic": [],
                "specialized": ["api-builder", "component-builder-nextjs"],
                "project": [],
            },
        )
        # Minimal orchestrator guide so sync_orchestrator_to_claude has content
        guide = root / ".agents" / "_generated" / "ORCHESTRATOR_GUIDE.md"
        guide.write_text("# Orchestrator Guide\n\nDetails.", encoding="utf-8")

        # Pre-existing CLAUDE.md template to be enriched
        claude_dir = root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "CLAUDE.md").write_text(
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

        compose_script = REPO_ROOT / ".edison" / "core" / "scripts" / "prompts" / "compose"
        assert compose_script.exists(), "compose script missing"

        result = run_with_timeout(
            [sys.executable, str(compose_script), "--sync-claude"],
            cwd=REPO_ROOT,
            env={**dict(**os.environ), "AGENTS_PROJECT_ROOT": str(root)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"compose --sync-claude failed: {result.stderr or result.stdout}"

        # Agents synced
        api_agent = claude_dir / "agents" / "api-builder.md"
        comp_agent = claude_dir / "agents" / "component-builder-nextjs.md"
        assert api_agent.exists()
        assert comp_agent.exists()

        # Orchestrator enriched with guide content
        claude_md = claude_dir / "CLAUDE.md"
        content = claude_md.read_text(encoding="utf-8")
        assert "Orchestrator Guide" in content
        assert "<!-- EDISON_ORCHESTRATOR_GUIDE_START -->" in content

        # config.json generated with roster
        config_path = claude_dir / "config.json"
        assert config_path.exists()
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        assert sorted(cfg["agents"]["specialized"]) == ["api-builder", "component-builder-nextjs"]

    @pytest.mark.integration
    def test_sync_claude_agents_flag_only_syncs_agents(self, isolated_project_env: Path) -> None:
        """compose --sync-claude-agents syncs agents without touching CLAUDE.md or config.json."""
        root = isolated_project_env
        _bootstrap_minimal_project(root)

        self._write_generated_agent(root, "feature-implementer")
        self._write_manifest(root, {"generic": ["feature-implementer"], "specialized": [], "project": []})

        claude_dir = root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text("# Claude Code Orchestrator\n\nBody.", encoding="utf-8")
        before = claude_md.read_text(encoding="utf-8")

        compose_script = REPO_ROOT / ".edison" / "core" / "scripts" / "prompts" / "compose"

        result = run_with_timeout(
            [sys.executable, str(compose_script), "--sync-claude-agents"],
            cwd=REPO_ROOT,
            env={**dict(**os.environ), "AGENTS_PROJECT_ROOT": str(root)},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"compose --sync-claude-agents failed: {result.stderr or result.stdout}"

        # Agent file created
        agent_path = claude_dir / "agents" / "feature-implementer.md"
        assert agent_path.exists()

        # CLAUDE.md and config.json untouched
        after = claude_md.read_text(encoding="utf-8")
        assert after == before
        assert not (claude_dir / "config.json").exists()


@pytest.mark.integration
def test_compose_claude_uses_generated_orchestrator() -> None:
    """scripts/prompts/compose --claude should use _generated orchestrator guide."""
    compose_script = REPO_ROOT / "scripts" / "prompts" / "compose"
    assert compose_script.exists(), "top-level compose script missing"

    result = run_with_timeout(
        [str(compose_script), "--claude"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"scripts/prompts/compose --claude failed: {result.stderr or result.stdout}"

    claude_path = REPO_ROOT / ".claude" / "CLAUDE.md"
    assert claude_path.exists(), ".claude/CLAUDE.md must be generated"

    content = claude_path.read_text(encoding="utf-8")
    # Phase 2C requirement: orchestrator must clearly reference the _generated guide
    assert (
        "<!-- Source: .agents/_generated/ORCHESTRATOR_GUIDE.md -->" in content
    ), "CLAUDE.md should declare .agents/_generated/ORCHESTRATOR_GUIDE.md as its source"


@pytest.mark.integration
def test_compose_claude_generates_agents_from_generated(tmp_path: Path) -> None:
    """scripts/prompts/compose --claude should materialize agents from _generated/agents."""
    # Use an isolated project root so we don't mutate the real .claude directory.
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)

    # Minimal Edison layout: defaults + config + _generated agents
    core_dir = project_root / ".edison" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    real_defaults = REPO_ROOT / ".edison" / "core" / "defaults.yaml"
    if real_defaults.exists():
        shutil.copy(real_defaults, core_dir / "defaults.yaml")
    else:
        (core_dir / "defaults.yaml").write_text("project:\n  name: test-project\n", encoding="utf-8")

    agents_dir = project_root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    real_config = REPO_ROOT / ".agents" / "config.yml"
    if real_config.exists():
        shutil.copy(real_config, agents_dir / "config.yml")
    else:
        (agents_dir / "config.yml").write_text("project:\n  name: test-project\n", encoding="utf-8")

    # Seed _generated agents by copying the real repo's composed agents.
    src_generated_agents = REPO_ROOT / ".agents" / "_generated" / "agents"
    dst_generated_agents = agents_dir / "_generated" / "agents"
    dst_generated_agents.mkdir(parents=True, exist_ok=True)
    if src_generated_agents.exists():
        for path in src_generated_agents.glob("*.md"):
            shutil.copy(path, dst_generated_agents / path.name)
    else:
        # Fallback: write a minimal api-builder agent so the adapter has something to project.
        dst_generated_agents.joinpath("api-builder.md").write_text(
            "# Agent: api-builder\n\n## Role\nAPI builder role.\n",
            encoding="utf-8",
        )

    compose_script = REPO_ROOT / "scripts" / "prompts" / "compose"
    env = {**os.environ, "AGENTS_PROJECT_ROOT": str(project_root)}

    result = run_with_timeout(
        [str(compose_script), "--claude"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert (
        result.returncode == 0
    ), f"scripts/prompts/compose --claude failed for isolated project: {result.stderr or result.stdout}"

    claude_agents_dir = project_root / ".claude" / "agents"
    assert claude_agents_dir.exists(), "compose --claude should create .claude/agents directory"

    api_agent = claude_agents_dir / "api-builder.md"
    assert api_agent.exists(), "compose --claude should materialize api-builder agent from _generated/agents"