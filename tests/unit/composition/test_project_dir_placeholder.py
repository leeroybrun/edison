from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.composers import CompositionEngine
from edison.core.composition.agents import AgentRegistry


def _write_core_agent(root: Path, name: str = "demo-agent", project_dir: str = ".edison") -> Path:
    agents_dir = root / project_dir / "core" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / f"{name}.md"
    path.write_text(
        "\n".join(
            [
                "# Agent: {{AGENT_NAME}}",
                "",
                "## Role",
                "Base role for {{AGENT_NAME}}.",
                "",
                "## Tools",
                "{{TOOLS}}",
                "",
                "## Guidelines",
                "{{GUIDELINES}}",
                "",
                "## Workflows",
                "- Core workflow step",
            ]
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def custom_project_dir(monkeypatch: pytest.MonkeyPatch) -> str:
    custom = ".custom-edison"
    monkeypatch.setenv("EDISON_paths__project_config_dir", custom)
    return custom


def test_claude_orchestrator_replaces_project_dir_placeholder(
    isolated_project_env: Path, custom_project_dir: str
) -> None:
    root = isolated_project_env
    engine = CompositionEngine(repo_root=root)
    claude_brief = engine.project_dir / "packs" / "clients" / "claude" / "CLAUDE.md"
    claude_brief.parent.mkdir(parents=True, exist_ok=True)
    claude_brief.write_text(
        "\n".join(
            [
                "# Claude Brief",
                "",
                "Load constitution:",
                "{{PROJECT_EDISON_DIR}}/_generated/constitutions/ORCHESTRATORS.md",
            ]
        ),
        encoding="utf-8",
    )

    out_path = engine.compose_claude_orchestrator(root / ".claude")
    content = out_path.read_text(encoding="utf-8")

    assert "{{PROJECT_EDISON_DIR}}" not in content
    assert f"{custom_project_dir}/_generated/constitutions/ORCHESTRATORS.md" in content
    assert ".edison/_generated" not in content


def test_generated_agents_use_relative_project_dir(
    isolated_project_env: Path, custom_project_dir: str
) -> None:
    root = isolated_project_env
    _write_core_agent(root, "delegation-expert", project_dir=custom_project_dir)
    registry = AgentRegistry(repo_root=root)
    assert "delegation-expert" in registry.discover_core_agents()

    engine = CompositionEngine(repo_root=root)
    results = engine.compose_claude_agents()

    agent_path = results.get("delegation-expert")
    assert agent_path is not None, "agent should be composed"
    assert agent_path.exists(), "agent prompt should be written to the configured project dir"
    content = agent_path.read_text(encoding="utf-8")

    assert "{{PROJECT_EDISON_DIR}}" not in content
    assert ".edison/_generated" not in content
    assert ".custom-edison/_generated" not in content
    assert "../constitutions/AGENTS.md" in content or "../../_generated/constitutions/AGENTS.md" in content
