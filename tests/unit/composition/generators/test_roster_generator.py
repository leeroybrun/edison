"""Integration test for roster generators (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.composition.generators import AgentRosterGenerator
from edison.core.registries.agents import AgentRegistry


def test_agent_roster_generator_writes_from_registry(tmp_path: Path) -> None:
    # Setup core agent
    project_agents = tmp_path / ".edison" / "agents"
    project_agents.mkdir(parents=True, exist_ok=True)
    (project_agents / "alpha.md").write_text(
        """# Alpha
<!-- SECTION: role -->Base role<!-- /SECTION: role -->
""",
        encoding="utf-8",
    )

    # Template for roster
    core_generators = tmp_path / "core" / "generators"
    core_generators.mkdir(parents=True, exist_ok=True)
    (core_generators / "AVAILABLE_AGENTS.md").write_text(
        "# Agents\n{{#each agents}}{{this.name}}\n{{/each}}", encoding="utf-8"
    )

    # Registry should pick up core agent
    gen = AgentRosterGenerator(project_root=tmp_path)
    gen.core_dir = tmp_path / "core"

    out_dir = tmp_path / ".edison" / "_generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = gen.write(out_dir)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert content.startswith("# Agents")
    assert len(content.splitlines()) > 1
