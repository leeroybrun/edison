from __future__ import annotations

from pathlib import Path

from edison.core.registries.agents import AgentRegistry


def test_agent_registry_reads_mcp_servers_from_frontmatter(
    isolated_project_env: Path,
) -> None:
    repo_root = isolated_project_env

    agents_dir = repo_root / ".edison" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "demo.md").write_text(
        "---\n"
        "description: Demo agent\n"
        "model: codex\n"
        "mcp_servers:\n"
        "  - playwright\n"
        "---\n"
        "\n"
        "# Demo\n",
        encoding="utf-8",
    )

    registry = AgentRegistry(project_root=repo_root)
    agent = registry.get("demo")
    assert agent is not None
    assert agent.mcp_servers == ["playwright"]

