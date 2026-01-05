from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import json
import os

import pytest
from edison.core.utils.subprocess import run_with_timeout

from edison.data import get_data_path
from tests.helpers.io_utils import write_generated_agent, write_orchestrator_manifest

_CUR = Path(__file__).resolve()

# Find the real edison repository root (development mode)
# This is needed for integration tests that run scripts
REPO_ROOT: Path | None = None
for parent in _CUR.parents:
    if (parent / "src" / "edison").exists() and (parent / "pyproject.toml").exists():
        REPO_ROOT = parent
        break

if REPO_ROOT is None:
    # Fallback: use bundled data location
    data_root = get_data_path("")
    REPO_ROOT = data_root.parent.parent.parent  # edison/data -> edison -> src -> repo


def _bootstrap_minimal_project(root: Path) -> None:
    """Populate isolated project root with minimal Edison config/layout."""
    # Use bundled Edison data instead of looking for legacy .edison/core
    bundled_defaults = get_data_path("config", "defaults.yaml")

    config_dir = root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    if bundled_defaults.exists():
        shutil.copy(bundled_defaults, config_dir / "defaults.yaml")
    else:
        # Minimal fallback configuration when defaults not present
        (config_dir / "defaults.yaml").write_text(
            "validation:\n  roster:\n    global: []\n    critical: []\n    specialized: []\n",
            encoding="utf-8",
        )

    # Project config.yml (minimal for testing)
    agents_dir = root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.yml").write_text("project:\n  name: test-project\n", encoding="utf-8")


class TestClaudeIntegrationE2E:

    @pytest.mark.integration
    def test_full_sync_pipeline_via_cli(self, isolated_project_env: Path) -> None:
        """compose --sync-claude syncs agents, orchestrator guide, and config.json into .claude/."""
        root = isolated_project_env
        _bootstrap_minimal_project(root)

        # Generated Edison artifacts
        write_generated_agent(root, "api-builder")
        write_generated_agent(root, "component-builder-nextjs")
        write_orchestrator_manifest(
            root,
            agents={
                "generic": [],
                "specialized": ["api-builder", "component-builder-nextjs"],
                "project": [],
            },
        )
        # Minimal orchestrator constitution (replaces ORCHESTRATOR_GUIDE.md - T-011)
        constitutions_dir = root / ".agents" / "_generated" / "constitutions"
        constitutions_dir.mkdir(parents=True, exist_ok=True)
        constitution = constitutions_dir / "ORCHESTRATOR.md"
        constitution.write_text("# Orchestrator Constitution\n\nDetails.", encoding="utf-8")

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

        # Look for compose script in development mode, skip if not available
        compose_script = REPO_ROOT / "scripts" / "prompts" / "compose" if REPO_ROOT else None
        if not compose_script or not compose_script.exists():
            import pytest
            pytest.skip("compose script not available in standalone Edison package")

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

        claude_md = claude_dir / "CLAUDE.md"
        assert claude_md.exists()

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

        write_generated_agent(root, "feature-implementer")
        write_orchestrator_manifest(root, agents={"generic": ["feature-implementer"], "specialized": [], "project": []})

        claude_dir = root / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        claude_md = claude_dir / "CLAUDE.md"
        claude_md.write_text("# Claude Code Orchestrator\n\nBody.", encoding="utf-8")
        before = claude_md.read_text(encoding="utf-8")

        compose_script = REPO_ROOT / "scripts" / "prompts" / "compose" if REPO_ROOT else None
        if not compose_script or not compose_script.exists():
            import pytest
            pytest.skip("compose script not available in standalone Edison package")

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
def test_compose_claude_generates_agents_from_generated(tmp_path: Path) -> None:
    """scripts/prompts/compose --claude should materialize agents from _generated/agents."""
    if not REPO_ROOT:
        pytest.skip("Repo root not found - test requires development environment")

    # Use an isolated project root so we don't mutate the real .claude directory.
    project_root = tmp_path / "project"
    project_root.mkdir(parents=True, exist_ok=True)

    # Minimal Edison layout: defaults + config + _generated agents
    config_dir = project_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    bundled_defaults = get_data_path("config", "defaults.yaml")
    if bundled_defaults.exists():
        shutil.copy(bundled_defaults, config_dir / "defaults.yaml")
    else:
        (config_dir / "defaults.yaml").write_text("project:\n  name: test-project\n", encoding="utf-8")

    agents_dir = project_root / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "config.yml").write_text("project:\n  name: test-project\n", encoding="utf-8")

    # Try to seed _generated agents from wilson-leadgen project if available
    wilson_leadgen = None
    for parent in Path(__file__).resolve().parents:
        if (parent / ".agents" / "_generated" / "agents").exists():
            wilson_leadgen = parent
            break

    src_generated_agents = wilson_leadgen / ".agents" / "_generated" / "agents" if wilson_leadgen else None
    dst_generated_agents = agents_dir / "_generated" / "agents"
    dst_generated_agents.mkdir(parents=True, exist_ok=True)
    if src_generated_agents and src_generated_agents.exists():
        for path in src_generated_agents.glob("*.md"):
            shutil.copy(path, dst_generated_agents / path.name)
    else:
        # Fallback: write a minimal api-builder agent so the adapter has something to project.
        dst_generated_agents.joinpath("api-builder.md").write_text(
            "# Agent: api-builder\n\n## Role\nAPI builder role.\n",
            encoding="utf-8",
        )

    compose_script = REPO_ROOT / "scripts" / "prompts" / "compose"
    if not compose_script.exists():
        pytest.skip("compose script not available in standalone Edison package")
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
