from __future__ import annotations

from edison.core.agents import AgentRegistry 
def test_nextjs_pack_declares_component_builder_agent() -> None:
    names = AgentRegistry().discover_pack_agent_names(["nextjs"])
    assert "component-builder-nextjs" in names


def test_prisma_pack_declares_database_architect_agent() -> None:
    names = AgentRegistry().discover_pack_agent_names(["prisma"])
    assert "database-architect-prisma" in names
