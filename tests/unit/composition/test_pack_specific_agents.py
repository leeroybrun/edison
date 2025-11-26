from __future__ import annotations

from edison.core.composition.agents import AgentRegistry
from edison.data import get_data_path

def test_nextjs_pack_declares_component_builder_agent() -> None:
    # Use the data directory as the "repo root" for pack discovery
    data_root = get_data_path("").parent  # Go up one level from data/ to edison/
    # AgentRegistry expects .edison/packs structure, so point to data parent
    # But packs are actually in data/packs, so we need to set up the path correctly
    # Actually, since edison/data/packs exists, we can use a special repo_root
    # that makes .edison/packs resolve to data/packs
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create symlink: tmpdir/.edison/packs -> edison/data/packs
        edison_dir = tmp_path / ".edison"
        edison_dir.mkdir()
        packs_link = edison_dir / "packs"
        packs_src = get_data_path("packs")
        packs_link.symlink_to(packs_src)

        registry = AgentRegistry(repo_root=tmp_path)
        names = registry.discover_pack_agent_names(["nextjs"])
        assert "component-builder-nextjs" in names


def test_prisma_pack_declares_database_architect_agent() -> None:
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        edison_dir = tmp_path / ".edison"
        edison_dir.mkdir()
        packs_link = edison_dir / "packs"
        from edison.data import get_data_path
        packs_src = get_data_path("packs")
        packs_link.symlink_to(packs_src)

        registry = AgentRegistry(repo_root=tmp_path)
        names = registry.discover_pack_agent_names(["prisma"])
        assert "database-architect-prisma" in names
